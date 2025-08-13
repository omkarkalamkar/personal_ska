# flake8: noqa
"""Module for programTrackTable calculator."""
from __future__ import annotations

import datetime
import operator
from logging import Logger
from typing import List, Union

from astropy.time import Time

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.constants import PROGRAM_TRACK_TABLE_SIZE, SKA_EPOCH


class ProgramTrackTableCalculator:
    """Class for programTrackTableCalculator."""

    right_ascension: str = ""
    declination: str = ""
    target_name: str = ""
    weather_data: dict
    azel_converter: AzElConverter
    elevation_limit: bool

    def __init__(
        self: ProgramTrackTableCalculator, component_manager, logger: Logger
    ) -> None:
        """
        Init method for ProgramTrackTableCalculator class.
        :param component_manager: DishLeafNode pointing device component
        manager object
        :type component_manager: DishLNComponentManager
        :param logger: logger
        :type logger: Logger
        :return: : None
        :rtype: None
        """
        self.component_manager = component_manager
        self.logger = logger
        self.track_table_time_stamp: datetime.datetime | None = None
        self.pointing_calculation_period: float = operator.truediv(
            self.component_manager.track_table_update_rate,
            PROGRAM_TRACK_TABLE_SIZE,
        )
        self.ptt_buffer_set = False
        self.track_table_scheduler = None

    def calculate_program_track_table(
        self: ProgramTrackTableCalculator,
        target_data: Union[str, List[str]],
        azel_converter: AzElConverter,
    ) -> list:
        """This method calculates programTrackTable.

        :param target_data: The name or RaDec for the target
        :type target_data: Union[str, List[str]]
        :return: list in the form of [TAI1, Az1, El1, TAI2, Az2,
            El2,,,,,,TAIn, Azn, Eln].
        :rtype: list
        """

        if isinstance(target_data, str):
            self.target_name = target_data
        else:
            self.right_ascension, self.declination = target_data
        self.azel_converter = azel_converter
        self.weather_data = self.azel_converter.weather_data
        program_track_table = []

        try:
            (
                time_stamp_list,
                tai_timestamp_list,
            ) = self.calculate_time_stamp_list()
            results: list = list(map(self.point, time_stamp_list))
            for result in results:
                if not self._is_elevation_within_mechanical_limits(result[1]):
                    message = (
                        "Minimum/maximum elevation limit has been reached."
                        + ("Source is not visible currently.")
                    )
                    raise Exception(message)
                if self.component_manager.wrap_sector_key:
                    result[0] = (
                        result[0] + 360 * self.component_manager.wrap_sector
                    )
                else:
                    # To support deprecated target key.
                    if not (
                        self.component_manager.azimuth_min_limit
                        < result[0]
                        < self.component_manager.azimuth_max_limit
                    ):
                        result[0] = self.fit_azimuth_in_observable_range(
                            result[0]
                        )

                program_track_table.append(tai_timestamp_list.pop(0))
                program_track_table.extend(
                    [round(result[0], 12), round(result[1], 12)]
                )
                self.track_table_scheduler.run(blocking=False)
                if (
                    self.ptt_buffer_set
                    and self.component_manager.mapping_scan_event.wait(
                        self.pointing_calculation_period
                    )
                ):
                    self.logger.debug(
                        "Stopping the ProgramTrackTable calculation."
                    )
                    break

            return program_track_table

        except Exception as exception:
            self.logger.exception(
                "Exception occured to calculate "
                + "program track table , Exception: %s",
                str(exception),
            )
            raise Exception(str(exception)) from exception

    def _is_elevation_within_mechanical_limits(
        self: ProgramTrackTableCalculator,
        el_value: float,
    ) -> bool:
        """Check if elevation is within mechanical limit.

        :param el_value: Elevation of the source.
        :type el_value: float
        :return: False if elevation is within the limit.
        :rtype: bool
        """
        if (
            not self.component_manager.elevation_min_limit
            <= el_value
            <= self.component_manager.elevation_max_limit
        ):
            self.elevation_limit = True
            message = "Minimum/maximum elevation limit has been reached." + (
                "Source is not visible currently."
            )
            self.logger.info(message)
            return False

        self.elevation_limit = False
        return True

    def calculate_time_stamp_list(self: ProgramTrackTableCalculator) -> tuple:
        """
        This methods calculates an list of requested timestamps
        (TrackTableEntries) with a requested time difference
        (PointingCalculationPeriod) and corresponding list of time
        in TAI format.

        :return: Tuple with list of timestamps (UTC) in string format and
            timestamp in TAI format.
        :rtype: tuple
        """
        time_stamp_list = []
        tai_timestamp_list = []
        try:
            for _ in range(PROGRAM_TRACK_TABLE_SIZE):
                timestamp_time_obj = Time(
                    self.track_table_time_stamp, scale="utc"
                )
                time_stamp_list.append(timestamp_time_obj)
                tai_time = self.convert_utc_to_tai(timestamp_time_obj)
                tai_timestamp_list.append(tai_time)

                self.track_table_time_stamp = (
                    self.track_table_time_stamp
                    + datetime.timedelta(
                        seconds=(self.pointing_calculation_period)
                    )
                )

        except ValueError as value_error:
            message = (
                "Exception occurred while calculating timestamp list: "
                + str(value_error)
            )
            self.logger.error(message)
            raise Exception(message) from value_error

        except Exception as exception:
            message = (
                "Exception occurred while calculating timestamp list: "
                + str(exception)
            )
            self.logger.exception(message)
            raise Exception(message) from exception

        return time_stamp_list, tai_timestamp_list

    def point(self: ProgramTrackTableCalculator, timestamp: str) -> list:
        """
        This method converts Target RaDec coordinates to the AzEl
        coordinates. It is called continuously from Configure command
        (in a thread) at interval of 50ms till the StopTrack command is
        invoked.

        :param timestamp: utc timestamp
        :type timestamp: str
        :return: Azimuth and Elevation coordinates (Az, El) of source.
        :rtype: list
        """
        try:
            if self.target_name:
                result = self.azel_converter.point_to_body(
                    self.target_name, timestamp
                )
                return result

            result = self.azel_converter.radec_to_azel(
                self.right_ascension,
                self.declination,
                timestamp,
            )
            return result
        except Exception as exception:
            self.logger.exception(
                "Failed to convert coordinates to AzEl: %s", str(exception)
            )
            raise Exception(str(exception)) from exception

    def convert_utc_to_tai(
        self: ProgramTrackTableCalculator, utc_time: float
    ) -> float:
        """
        This method converts utc time to tai format time.
        :param: utc_time: time in utc (seconds)
        :type utc_time: float
        :returns: Time in TAI format (seconds)
        :rtype: float
        """
        tai_time = 0.0
        try:
            ska_epoch_utc = Time(SKA_EPOCH, scale="utc")
            tai_time = utc_time.unix_tai - ska_epoch_utc.unix_tai

        except ValueError as value_error:
            message = (
                "Exception occurred while converting utc time to tai format: "
                + str(value_error)
            )
            self.logger.error(message)
            raise Exception(message) from value_error

        except Exception as exception:
            message = (
                "Exception occurred while converting utc time to tai format: "
                + str(exception)
            )
            self.logger.exception(message)
            raise Exception(message) from exception

        return tai_time

    def fit_azimuth_in_observable_range(
        self, calculated_azimuth: float
    ) -> float:
        """
        This method fits the calculated azimuth to the dish's observable
        azimuth range.
        :param: calculated_azimuth: Azimuth in degrees
        :type calculated_azimuth: float
        :returns: Azimuth in degrees
        :rtype: float
        """
        azimuth: float
        try:
            if calculated_azimuth > self.component_manager.azimuth_max_limit:
                azimuth = calculated_azimuth - 360
            elif calculated_azimuth < self.component_manager.azimuth_min_limit:
                azimuth = calculated_azimuth + 360
        except ValueError as exception:
            exception_message = (
                "Exception occurred while fitting azimuth in the dish's"
                + " observable range: %s",
                exception,
            )
            self.logger.exception(exception_message)
            raise Exception(exception_message) from exception
        return azimuth
