# flake8: noqa
"""Module for programTrackTable calculator."""
from __future__ import annotations

import datetime
from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from typing import List, Union

from astropy.time import Time

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.constants import SKA_EPOCH


class ProgramTrackTableCalculator:
    """Class for programTrackTableCalculator."""

    right_ascension: str = ""
    declination: str = ""
    target_name: str = ""
    weather_data: dict
    azel_converter: AzElConverter
    track_table_time_stamp: datetime.datetime
    track_table_start_time: float
    elevation_limit: bool

    def __init__(
        self: ProgramTrackTableCalculator, component_manager, logger: Logger
    ) -> None:
        """
        Init method for ProgramTrackTableCalculator class.
        :param component_manager: Dish Leaf Node component manager object
        :type component_manager: DishLNComponentManager
        :param logger: logger
        :type logger: Logger
        :return: : None
        :rtype: None
        """
        self.component_manager = component_manager
        self.logger = logger

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

        with ThreadPoolExecutor(max_workers=2) as executor:
            (
                time_stamp_list,
                tai_timestamp_list,
            ) = self.calculate_time_stamp_list()
            results = executor.map(self.point, time_stamp_list)
        try:
            for result in results:
                if not self._is_elevation_within_mechanical_limits(result[1]):
                    tai_timestamp_list.pop(0)
                    continue
                if result[0] < 0:
                    result[0] = 360 - abs(result[0])

                program_track_table.append(tai_timestamp_list.pop(0))
                program_track_table.extend(
                    [round(result[0], 12), round(result[1], 12)]
                )

                if self.component_manager.get_track_process_event_status():
                    self.logger.debug("Stopping the ProgramTrackTable Thread.")
                    break
        except Exception as exception:
            self.logger.error(exception)

        return program_track_table

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
            self.logger.info(
                "Minimum/maximum elevation limit has been reached."
                + " Source is not visible currently."
            )
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
        self.track_table_start_time = self.track_table_time_stamp.timestamp()
        time_stamp_list = []
        tai_timestamp_list = []
        for _ in range(self.component_manager.track_table_entries):
            timestamp_sec = self.track_table_time_stamp.timestamp()
            timestamp_str = self.convert_timestamp(timestamp_sec)
            time_stamp_list.append(timestamp_str)

            tai_time = self.convert_utc_to_tai(timestamp_sec)
            tai_timestamp_list.append(tai_time)

            self.track_table_time_stamp = (
                self.track_table_time_stamp
                + datetime.timedelta(
                    milliseconds=(
                        self.component_manager.pointing_calculation_period
                    )
                )
            )
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
        if self.target_name:
            return self.azel_converter.point_to_body(
                self.target_name, timestamp
            )
        return self.azel_converter.radec_to_azel(
            self.right_ascension,
            self.declination,
            timestamp,
        )

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

        ska_epoch_utc = Time(SKA_EPOCH, scale="utc")
        return utc_time - ska_epoch_utc.unix_tai

    def convert_timestamp(
        self: ProgramTrackTableCalculator, timestamp_seconds: float
    ) -> str:
        """
        Converts the floating point timestamp in seconds to a utc
        timestamp with format -> %Y-%m-%d %H:%M:%S

        :param timestamp_seconds: Input timestamp with time in seconds
        :type timestamp_seconds: float
        :return: Timestamp with format "%Y-%m-%d %H:%M:%S".
        :rtype: string
        """
        timestamp = datetime.datetime.utcfromtimestamp(
            timestamp_seconds
        ).strftime("%Y-%m-%d %H:%M:%S")
        return timestamp
