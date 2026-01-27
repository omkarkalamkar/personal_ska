"""The module for AutoStow Class"""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from typing import Optional

import numpy as np
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DishMode

from ska_tmc_dishleafnode.enums.stow_status import StowStatus


class RepeatedTimer(threading.Timer):
    """Class for RepeatedTimer."""

    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class AutoStow:
    """Class for Auto stow functionality"""

    def __init__(
        self,
        component_manager,
        logger,
        temp_delta: float = 4.5,
        time_delta: float = 1000,
        max_temp_threshold: float = 40.0,
        min_temp_threshold: float = -5.0,
        wind_speed_threshold: float = 13.5,
        gust_speed_threshold: float = 20.0,
        mean_wind_speed_duration: float = 600,
        mean_gust_speed_duration: float = 3,
        operational_wind_speed_duration: float = 1000,
        operational_wind_speed_threshold: float = 10.0,
        operational_perc_mean_diff_duration: float = 600,
        operational_perc_mean_diff_threshold: float = 4.5,
        percentile_for_diff: float = 95.0,
    ):
        self.component_manager = component_manager
        self.__wind_speeds: dict = defaultdict(list)
        self.__gust_speeds: dict = defaultdict(list)
        self.__operational_wind_speeds: dict = defaultdict(list)
        self.__operational_perc_mean_speeds: dict = defaultdict(list)

        self.rate_of_change_temp: dict = {}
        self.wind_lock = threading.Lock()
        self.gust_lock = threading.Lock()
        self.op_wind_lock = threading.Lock()
        self.op_perc_lock = threading.Lock()

        self.logger: logging.Logger = logger
        self.temp_lock = threading.Lock()
        self.poll_lock = threading.Lock()
        self.poll_threads: list[threading.Timer] = []
        self.__polled_temperatures: dict = defaultdict(list)
        self.__percentile_for_diff = percentile_for_diff
        self.__temperatures: dict = {}
        self.initial_mark_achieved: dict[str, threading.Event] = defaultdict(
            threading.Event
        )
        self.temp_update: dict[str, threading.Event] = defaultdict(
            threading.Event
        )
        self.__max_temp_threshold: float = max_temp_threshold
        self.__min_temp_threshold: float = min_temp_threshold
        self.__wind_speed_threshold: float = wind_speed_threshold
        self.__gust_speed_threshold: float = gust_speed_threshold
        self.__mean_wind_speed_duration: float = mean_wind_speed_duration
        self.__mean_gust_speed_duration: float = mean_gust_speed_duration
        self.__operational_wind_speed_duration: float = (
            operational_wind_speed_duration
        )
        self.__operational_wind_speed_threshold: float = (
            operational_wind_speed_threshold
        )
        self.__operational_perc_mean_diff_duration: float = (
            operational_perc_mean_diff_duration
        )
        self.__operational_perc_mean_diff_threshold: float = (
            operational_perc_mean_diff_threshold
        )
        self.__time_delta: float = time_delta
        self.__temp_delta: float = temp_delta
        self.temp_threads: dict[str, threading.Thread] = {}
        self.wind_timer: Optional[RepeatedTimer] = None
        self.gust_timer: Optional[RepeatedTimer] = None
        self.operational_wind_timer: Optional[RepeatedTimer] = None
        self.perc_mean_diff_timer: Optional[RepeatedTimer] = None
        self.update_lock = threading.Lock()

    def __del__(self):
        """Destructor to manage the cleanup."""
        self.cancel_timer(self.wind_timer)
        self.cancel_timer(self.gust_timer)
        self.cancel_timer(self.operational_wind_timer)
        self.cancel_timer(self.perc_mean_diff_timer)
        if self.temp_threads:
            for key in self.component_manager.temperature_tracking:
                self.component_manager.temperature_tracking[key].clear()
            for wms, thread in self.temp_threads.items():
                self.initial_mark_achieved[wms].set()
                thread.join(timeout=5)
            for poller in self.poll_threads:
                poller.join()
            self.polled_temperatures.clear()
            self.initial_mark_achieved.clear()
            self.temp_update.clear()

    def start_temp_tracking(self, wms: str) -> None:
        """Starts temperature tracking."""
        temp_thread = threading.Thread(
            target=self.roc_temp, args=[wms], daemon=True
        )
        temp_thread.start()
        self.temp_threads[wms] = temp_thread

    def update_wind_speed(self, wms: str, speed: float):
        """Updates the wind speed in required lists."""
        self.wind_speeds[wms].append(speed)
        self.gust_speeds[wms].append(speed)
        self.operational_wind_speeds[wms].append(speed)
        self.operational_perc_mean_speeds[wms].append(speed)

    def start_wind_tracking(self) -> None:
        """Starts wind based tracking"""
        if not self.wind_timer or not self.wind_timer.is_alive():
            self.wind_timer = RepeatedTimer(
                self.mean_wind_speed_duration,
                self.calculate_mean_wind_speeds,
                args=(
                    self.wind_speeds,
                    self.wind_speed_threshold,
                    "wind_speed_mean",
                ),
            )
            self.wind_timer.daemon = True
            self.wind_timer.start()
        if not self.gust_timer or not self.gust_timer.is_alive():
            self.gust_timer = RepeatedTimer(
                self.mean_gust_speed_duration,
                self.calculate_mean_wind_speeds,
                args=(
                    self.gust_speeds,
                    self.gust_speed_threshold,
                    "gust_wind_speed_mean",
                ),
            )
            self.gust_timer.daemon = True
            self.gust_timer.start()
        if (
            not self.operational_wind_timer
            or not self.operational_wind_timer.is_alive()
        ):
            self.operational_wind_timer = RepeatedTimer(
                self.operational_wind_speed_duration,
                self.calculate_mean_wind_speeds,
                args=(
                    self.operational_wind_speeds,
                    self.operational_wind_speed_threshold,
                    "operational_wind_speed_mean",
                ),
            )
            self.operational_wind_timer.daemon = True
            self.operational_wind_timer.start()
        if (
            not self.perc_mean_diff_timer
            or not self.perc_mean_diff_timer.is_alive()
        ):
            self.perc_mean_diff_timer = RepeatedTimer(
                self.operational_perc_mean_diff_duration,
                self.calculate_diff_precentile_average,
                args=(
                    self.operational_perc_mean_speeds,
                    self.operational_perc_mean_diff_threshold,
                    "operational_perc_mean_diff",
                ),
            )
            self.perc_mean_diff_timer.daemon = True
            self.perc_mean_diff_timer.start()

    @property
    def max_temp_threshold(self) -> float:
        """Property for maximum temperature threshold"""
        return self.__max_temp_threshold

    @max_temp_threshold.setter
    def max_temp_threshold(self, temp: float) -> None:
        """Setter to update the maximum temperature threshold"""
        self.__max_temp_threshold = temp

    @property
    def min_temp_threshold(self) -> float:
        """Property for minimum temperature threshold"""
        return self.__min_temp_threshold

    @min_temp_threshold.setter
    def min_temp_threshold(self, temp: float) -> None:
        """Setter to update the minimum temperature threshold"""
        self.__min_temp_threshold = temp

    @property
    def wind_speed_threshold(self) -> float:
        """Property for wind speed threshold"""
        return self.__wind_speed_threshold

    @wind_speed_threshold.setter
    def wind_speed_threshold(self, wind_speed: float) -> None:
        """Setter to update the wind speed threshold"""
        self.cancel_timer(self.wind_timer)
        self.__wind_speed_threshold = wind_speed
        self.wind_speeds.clear()

    @property
    def gust_speed_threshold(self) -> float:
        """Property for gust speed threshold"""
        with self.update_lock:
            return self.__gust_speed_threshold

    @gust_speed_threshold.setter
    def gust_speed_threshold(self, wind_speed: float) -> None:
        """Setter to update the gust speed threshold"""
        with self.update_lock:
            self.cancel_timer(self.gust_timer)
            self.__gust_speed_threshold = wind_speed
            self.gust_speeds.clear()

    @property
    def mean_wind_speed_duration(self) -> float:
        """Property for mean wind speed duration"""

        return self.__mean_wind_speed_duration

    @mean_wind_speed_duration.setter
    def mean_wind_speed_duration(self, wind_speed: float) -> None:
        """Setter to update the mean wind speed duration"""
        self.cancel_timer(self.wind_timer)

        self.__mean_wind_speed_duration = wind_speed
        self.wind_speeds.clear()

    @property
    def mean_gust_speed_duration(self) -> float:
        """Property for mean gust speed duration"""
        return self.__mean_gust_speed_duration

    @mean_gust_speed_duration.setter
    def mean_gust_speed_duration(self, wind_speed: float) -> None:
        """Setter to update the mean gust speed duration"""
        self.cancel_timer(self.gust_timer)
        self.__mean_gust_speed_duration = wind_speed
        self.gust_speeds.clear()

    @property
    def operational_wind_speed_duration(self) -> float:
        """Operation requirement wind duration"""
        return self.__operational_wind_speed_duration

    @operational_wind_speed_duration.setter
    def operational_wind_speed_duration(self, duration: float) -> None:
        """Operation requirement wind duration"""
        self.cancel_timer(self.operational_wind_timer)
        self.__operational_wind_speed_duration = duration

    @property
    def operational_perc_mean_diff_duration(self) -> float:
        """Operation requirement wind duration"""
        return self.__operational_perc_mean_diff_duration

    @operational_perc_mean_diff_duration.setter
    def operational_perc_mean_diff_duration(self, duration: float) -> None:
        """Operation requirement wind duration"""
        self.cancel_timer(self.perc_mean_diff_timer)
        self.__operational_perc_mean_diff_duration = duration

    @property
    def operational_wind_speed_threshold(self) -> float:
        """Operation requirement wind threshold"""
        return self.__operational_wind_speed_threshold

    @operational_wind_speed_threshold.setter
    def operational_wind_speed_threshold(self, speed: float) -> None:
        """Operation requirement wind threshold"""
        self.cancel_timer(self.operational_wind_timer)
        self.__operational_wind_speed_threshold = speed

    @property
    def operational_perc_mean_diff_threshold(self) -> float:
        """Operation requirement wind threshold"""
        return self.__operational_perc_mean_diff_threshold

    @operational_perc_mean_diff_threshold.setter
    def operational_perc_mean_diff_threshold(self, speed: float) -> None:
        """Operation requirement wind threshold"""
        self.cancel_timer(self.perc_mean_diff_timer)
        self.__operational_perc_mean_diff_threshold = speed

    @property
    def percentile_for_diff(self) -> float:
        """Operation requirement wind threshold"""
        return self.__percentile_for_diff

    @percentile_for_diff.setter
    def percentile_for_diff(self, percentile: float) -> None:
        """Operation requirement wind threshold"""
        self.__percentile_for_diff = percentile

    @property
    def temp_delta(self) -> float:
        """Property of Temperature Delta"""
        return self.__temp_delta

    @temp_delta.setter
    def temp_delta(self, delta: float) -> None:
        """Setter to update temperature delta."""
        self._temp_delta = delta

    @property
    def time_delta(self) -> float:
        """Property of Time Delta"""
        return self.__time_delta

    @time_delta.setter
    def time_delta(self, delta: float) -> None:
        """Setter to update time delta."""
        try:
            self.__time_delta = delta
            if self.temp_threads:
                for key in self.component_manager.temperature_tracking:
                    self.component_manager.temperature_tracking[key].clear()
                for poller in self.poll_threads:
                    poller.join()
                self.poll_threads.clear()
                for wms, thread in self.temp_threads.items():
                    self.initial_mark_achieved[wms].set()
                    thread.join()
                self.temp_threads.clear()
                self.polled_temperatures.clear()
                self.initial_mark_achieved.clear()
                self.temp_update.clear()
        except Exception as e:
            self.logger.exception(e)

    @property
    def temperatures(self) -> dict:
        """Property to manage temperature of all the weather stations."""
        with self.temp_lock:
            return self.__temperatures

    @property
    def polled_temperatures(self) -> dict:
        """Property to store polled the temperatures."""
        with self.poll_lock:
            return self.__polled_temperatures

    @property
    def wind_speeds(self):
        """Wind speed dictionary property."""
        with self.wind_lock:
            return self.__wind_speeds

    @property
    def operational_wind_speeds(self):
        """Wind speed dictionary property."""
        with self.op_wind_lock:
            return self.__operational_wind_speeds

    @property
    def operational_perc_mean_speeds(self):
        """Wind speed dictionary property."""
        with self.op_perc_lock:
            return self.__operational_perc_mean_speeds

    @property
    def gust_speeds(self):
        """Gust speed dictionary property."""
        with self.gust_lock:
            return self.__gust_speeds

    def cancel_timer(self, timer: threading.Timer):
        """Method to cancel ongoing timer thread."""
        if timer and timer.is_alive():
            timer.cancel()

    def _task_callback(self, **kwargs):
        """Method for handling setstowmode command result."""
        result = kwargs.get("result", None)
        exception = kwargs.get("exception", None)
        if not result:
            pass
        elif result[0] == ResultCode.OK:
            self.logger.info("auto stow completed")
        elif result[0] == ResultCode.FAILED:
            message = (
                "auto stow failed with result %s and exception %s",
                result,
                exception,
            )
            # can be utilised to expose failures in a attribute
            self.component_manager.update_auto_stow_failures(message)
            self.logger.info(message)

    def calculate_diff_precentile_average(
        self, wind_data: list, wind_threshold: float, attribute_to_update: str
    ):
        """Method to calculate difference between percentile
        and mean average speed of wind."""
        with tango.EnsureOmniThread():
            try:
                wind_speed_diffs: list = []
                wind_speeds: dict = wind_data.copy()
                wind_data.clear()

                for _, wind_speed in wind_speeds.items():
                    data = np.array(wind_speed)
                    mean = data.mean()
                    percentile = np.percentile(data, self.percentile_for_diff)
                    diff = abs(percentile - mean)
                    wind_speed_diffs.append(diff)
                if wind_speed_diffs:
                    wind_speed_diff = max(wind_speed_diffs)
                else:
                    wind_speed_diff = 0
                setattr(
                    self.component_manager,
                    attribute_to_update,
                    wind_speed_diff,
                )
                if wind_speed_diff > wind_threshold:
                    self.logger.info(
                        "Invoking auto stow based on mean wind speed"
                        "and 95th percentile difference %s %s",
                        wind_speed_diff,
                        wind_speed_diffs,
                    )
                    self.invoke_auto_stow()
            except Exception as exception:
                message = (
                    "Exception occured while calculating wind mean speed %s",
                    exception,
                )
                self.component_manager.update_auto_stow_failures(message)
                self.logger.exception(message)

    def calculate_mean_wind_speeds(
        self, wind_data: list, wind_threshold: float, attribute_to_update: str
    ):
        """Method to calculate mean wind speed."""
        with tango.EnsureOmniThread():
            try:
                wind_speed_means: list = []
                wind_speeds: dict = wind_data.copy()
                wind_data.clear()

                for _, wind_speed in wind_speeds.items():
                    wind_speed_means.append(np.array(wind_speed).mean())

                if wind_speed_means:
                    wind_speed_mean = max(wind_speed_means)
                else:
                    wind_speed_mean = 0
                setattr(
                    self.component_manager,
                    attribute_to_update,
                    wind_speed_mean,
                )
                if wind_speed_mean > wind_threshold:
                    self.logger.info(
                        "Invoking auto stow based on mean wind speed %s %s",
                        wind_speed_mean,
                        wind_speed_means,
                    )
                    self.invoke_auto_stow()

            except Exception as exception:
                message = (
                    "Exception occured while calculating wind mean speed %s",
                    exception,
                )
                self.component_manager.update_auto_stow_failures(message)
                self.logger.exception(message)

    def invoke_auto_stow(self):
        """Method to start temperature."""
        try:
            if (
                self.component_manager.get_dish_mode() != DishMode.STOW
                and self.component_manager.stow_status
                != StowStatus.STOW_STARTED
            ):
                self.component_manager.setstowmode(self._task_callback)

        except Exception as exception:
            message = (
                "Exception occured while invoking setstowmode %s",
                exception,
            )
            self.component_manager.update_auto_stow_failures(message)
            self.logger.exception(message)

    def _one_sec_poll(self, wms: str):
        """Method to poll temperature every second."""
        while self.component_manager.temperature_tracking[wms].is_set():
            start_time = time.perf_counter()
            self.polled_temperatures[wms].append(self.temperatures[wms])
            # once the initial mark(time delta is reached),
            # the comparision loop starts
            temp = self.polled_temperatures[wms].copy()

            if (
                len(temp) == self.time_delta
                and not self.initial_mark_achieved[wms].is_set()
            ):
                self.initial_mark_achieved[wms].set()
            # if the polled data is more than the time delta it is removed.
            elif len(temp) > self.time_delta:
                self.polled_temperatures[wms].pop(0)
            # notify the change in temperature
            self.temp_update[wms].set()

            end_time = time.perf_counter()
            time.sleep(1 - (end_time - start_time))

    def roc_temp(self, wms: str):
        """Method to calculate the rate of change of temperature."""
        with tango.EnsureOmniThread():
            try:
                poll_thread = threading.Thread(
                    target=self._one_sec_poll, args=[wms], daemon=True
                )
                poll_thread.start()
                self.poll_threads.append(poll_thread)

                self.initial_mark_achieved[wms].wait()

                while self.component_manager.temperature_tracking[
                    wms
                ].is_set():
                    if not self.temp_update[wms].wait(timeout=1):
                        continue
                    self.temp_update[wms].clear()
                    temps = self.polled_temperatures[wms].copy()
                    self.polled_temperatures[wms].pop(0)
                    roc = abs(temps[-1] - temps[0])
                    self.rate_of_change_temp[wms] = roc

                    if roc > self.temp_delta:
                        self.logger.info(
                            "rate of change :%s for station: %s", roc, wms
                        )
                        self.invoke_auto_stow()
                    self.component_manager.rate_of_change_temperature = (
                        self.rate_of_change_temp
                    )
            except Exception as exception:
                message = (
                    "Exception occured while checking"
                    "for rate of change of temperature %s",
                    exception,
                )
                self.component_manager.update_auto_stow_failures(message)

                self.logger.exception(message)
