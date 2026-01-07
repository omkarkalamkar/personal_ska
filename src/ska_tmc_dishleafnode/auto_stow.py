"""The module for AutoStow Class"""

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
        self.temp_lock = threading.Lock()
        self.__previous_temperature = self.component_manager.temperature

    @property
    def previous_temperature(self) -> float:
        """Previous temperature for rate of change calculation."""
        with self.temp_lock:
            return self.__previous_temperature

    @previous_temperature.setter
    def previous_temperature(self, temperature: float):
        """Setter for previous temperature

        :param temperature: temperature to set.
        :type temperature: float
        """
        with self.temp_lock:
            self.__previous_temperature = temperature

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
        self.logger.info("%s", time.time())
        wind_speed_means: list = []
        wind_speeds: dict = self.wind_speeds.copy()
        self.wind_speeds.clear()

        def _task_callback(**kwargs):
            result = kwargs.get("result", None)
            if not result:
                pass
            elif result[0] == ResultCode.OK:
                self.logger.info("auto stow completed")
            elif result[0] == ResultCode.FAILED:
                self.logger.info("auto stow failed.")

        for _, wind_speed in wind_speeds.items():
            wind_speed_means.append(np.array(wind_speed).mean())
        wind_speed_mean = max(wind_speed_means)
        self.logger.info(
            "%s max mean speed is: %s from %s",
            time.time(),
            wind_speed_mean,
            wind_speed_means,
        )
        self.component_manager.wind_speed_mean = wind_speed_mean
        if wind_speed_mean >= self.wind_threshold:
            if (
                self.component_manager.get_dish_mode() != DishMode.STOW
                and self.component_manager.stow_status
                != StowStatus.STOW_STARTED
            ):
                self.component_manager.setstowmode(_task_callback)

    def check_gusts(self):
        """Method to calculate gust speed."""
        gust_speeds: dict = self.gust_speeds.copy()
        self.gust_speeds.clear()
        gust_speed_means: list = []

        def _task_callback(**kwargs):
            result = kwargs.get("result", None)
            if not result:
                pass
            elif result[0] == ResultCode.OK:
                self.logger.info("auto stow completed")
            elif result[0] == ResultCode.FAILED:
                self.logger.info("auto stow failed.")

        for _, gust_speed in gust_speeds.items():
            gust_speed_means.append(np.array(gust_speed).mean())
        gust_wind_speed_mean = max(gust_speed_means)
        self.logger.info(
            "%s max gust speed mean is: %s from %s",
            time.time(),
            gust_wind_speed_mean,
            gust_speed_means,
        )
        self.component_manager.gust_wind_speed_mean = gust_wind_speed_mean
        if gust_wind_speed_mean >= self.gust_threshold:
            if (
                self.component_manager.get_dish_mode() != DishMode.STOW
                and self.component_manager.stow_status
                != StowStatus.STOW_STARTED
            ):
                self.component_manager.setstowmode(_task_callback)

    def temperature_based_auto_stow(self):
        """Method to start temperature."""

        def _task_callback(**kwargs):
            result = kwargs.get("result", None)
            if not result:
                pass
            elif result[0] == ResultCode.OK:
                self.logger.info("auto stow completed")
            elif result[0] == ResultCode.FAILED:
                self.logger.info("auto stow failed.")

        if (
            self.component_manager.get_dish_mode() != DishMode.STOW
            and self.component_manager.stow_status != StowStatus.STOW_STARTED
        ):
            self.component_manager.setstowmode(_task_callback)

    def change_of_rate_temperature_auto_stow(self):
        """Method to start temperature."""
        current_temperature = self.component_manager.temperature
        rate_of_change: float = abs(
            current_temperature - self.previous_temperature
        )
        self.logger.info(
            "%s rate of change of temp: %s", time.time(), rate_of_change
        )
        self.component_manager.rate_of_change_temperature = rate_of_change
        if rate_of_change > self.temp_delta:
            self.temperature_based_auto_stow()
        self.previous_temperature = current_temperature

