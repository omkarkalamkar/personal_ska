"""The module for AutoStow Class"""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict

import numpy as np
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
        wind_threshold: float = 13.5,
        gust_threshold: float = 20,
        temp_delta: float = 4.5,
        time_delta: float = 1000,
    ):
        self.component_manager = component_manager
        self.__wind_speeds: dict = defaultdict(list)
        self.__gust_speeds: dict = defaultdict(list)
        self.wind_lock = threading.Lock()
        self.gust_lock = threading.Lock()
        self.wind_threshold: float = wind_threshold
        self.gust_threshold: float = gust_threshold
        self.logger: logging.Logger = logger
        self.temp_delta: float = temp_delta
        self.time_delta: float = time_delta
        self.temp_lock = threading.Lock()
        self.poll_threads: list = []
        self.__polled_temperatures: dict = defaultdict(list)
        self.__temperatures: dict = {}
        self.initial_mark_achieved: dict[str, threading.Event] = defaultdict(
            threading.Event
        )
        self.temp_update: dict[str, threading.Event] = defaultdict(
            threading.Event
        )

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

    @property
    def temperatures(self) -> dict:
        """Property to manage temperature of all the weather stations."""
        with self.temp_lock:
            return self.__temperatures

    @property
    def polled_temperatures(self) -> dict:
        """Property to store polled the temperatures."""
        with self.temp_lock:
            return self.__polled_temperatures

    @property
    def wind_speeds(self):
        """Wind speed dictionary property."""
        with self.wind_lock:
            return self.__wind_speeds

    @property
    def gust_speeds(self):
        """Gust speed dictionary property."""
        with self.gust_lock:
            return self.__gust_speeds

    def calculate_mean_wind_speed(self):
        """Method to calculate mean wind speed."""
        try:
            wind_speed_means: list = []
            wind_speeds: dict = self.wind_speeds.copy()
            self.wind_speeds.clear()

            for _, wind_speed in wind_speeds.items():
                wind_speed_means.append(np.array(wind_speed).mean())
            wind_speed_mean = max(wind_speed_means)
            self.component_manager.wind_speed_mean = wind_speed_mean
            if wind_speed_mean >= self.wind_threshold:
                self.logger.info(
                    "Invoking auto stow based on mean wind speed %s",
                    wind_speed_mean,
                )
                self.invoke_auto_stow()

        except Exception as exception:
            message = (
                "Exception occured while calculating wind mean speed %s",
                exception,
            )
            self.component_manager.update_auto_stow_failures(message)
            self.logger.exception(message)

    def check_gusts(self):
        """Method to calculate gust speed."""
        try:
            gust_speeds: dict = self.gust_speeds.copy()
            self.gust_speeds.clear()
            gust_speed_means: list = []

            for _, gust_speed in gust_speeds.items():
                gust_speed_means.append(np.array(gust_speed).mean())
            gust_wind_speed_mean = max(gust_speed_means)
            self.component_manager.gust_wind_speed_mean = gust_wind_speed_mean
            if gust_wind_speed_mean >= self.gust_threshold:
                self.logger.info(
                    "Invoking auto stow based on mean gust speed %s",
                    gust_wind_speed_mean,
                )
                self.invoke_auto_stow()
        except Exception as exception:
            message = (
                "Exception occured while calculating gust mean speed %s",
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
        while self.component_manager.temperature_tracking[wms]:
            start_time = time.perf_counter()
            self.polled_temperatures[wms].append(self.temperatures[wms])
            self.logger.info(
                "%s %s", len(self.polled_temperatures[wms]), time.time()
            )
            # once the initial mark(time delta is reached),
            # the comparision loop starts
            if (
                len(self.polled_temperatures[wms]) == self.time_delta
                and not self.initial_mark_achieved[wms].is_set()
            ):
                self.initial_mark_achieved[wms].set()
            # if the polled data is more than the time delta it is removed.
            elif len(self.polled_temperatures[wms]) > self.time_delta:
                self.polled_temperatures[wms].pop(0)
            # notify the change in temperature
            self.temp_update[wms].set()
            end_time = time.perf_counter()
            time.sleep(1 - (end_time - start_time))

    def roc_temp(self, wms: str):
        """Method to calculate the rate of change of temperature."""
        try:
            poll_thread = threading.Thread(
                target=self._one_sec_poll, args=[wms], daemon=True
            )
            poll_thread.start()
            self.poll_threads.append(poll_thread)

            self.initial_mark_achieved[wms].wait()

            while (
                self.component_manager.temperature_tracking[wms]
                and self.temp_update[wms].wait()
            ):
                self.temp_update[wms].clear()
                self.logger.info("%s", len(self.polled_temperatures))
                temps = self.polled_temperatures[wms].copy()
                self.polled_temperatures[wms].pop(0)
                self.logger.info("%s %s", temps[-1], temps[0])
                if abs(temps[-1] - temps[0]) > self.temp_delta:
                    self.logger.info(
                        "roc %s %s", abs(temps[-1] - temps[0]), wms
                    )
                    self.invoke_auto_stow()
        except Exception as exception:
            message = (
                "Exception occured while checking"
                "for rate of change of temperature %s",
                exception,
            )
            self.component_manager.update_auto_stow_failures(message)

            self.logger.exception(message)
