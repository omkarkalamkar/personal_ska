"""
This module provides an implementation of the Dish Leaf Node
pointing device component manager.
"""

from __future__ import annotations
import datetime
from typing import List

import sched
import time
from logging import Logger

from astropy.utils import iers
from astropy.time import Time
from ska_tmc_common.tmc_component_manager import BaseTmcComponentManager
from ska_tmc_dishleafnode.constants import IERS_DATA_STORAGE_PATH, SKA_EPOCH

from ska_tmc_dishleafnode.dishln_pointing_device.utilities.az_el_converter import (
    AzElConverter,
)
from ska_tmc_dishleafnode.dishln_pointing_device.utilities.program_track_table_calculator import (
    ProgramTrackTableCalculator,
)


class DishlnPointingDataComponentManager(BaseTmcComponentManager):
    """
    A component manager for The Dish leaf node pointing device component.
    """

    # pylint: disable=unused-argument
    def __init__(self, logger: Logger):
        """
        Initialise a new ComponentManager instance.

        :param logger: a logger for this component manager
        :param dishln_pointing_device_name: name of the dish
            pointing device
        """

        super().__init__(logger)
        self.logger = logger
        self.elevation = 0.0
        self.azimuth = 0.0
        self.elevation_max_limit = 0.0
        self.elevation_min_limit = 0.0
        self.el_limit = False
        self.iers_a = None
        self.track_table_scheduler = sched.scheduler(time.time, time.sleep)
        self.pointing_calculation_period: int = 100
        self.track_table_entries: int = 50
        self.track_table_advance_sec: float = 6
        self.track_table_calculator = ProgramTrackTableCalculator(
            self, self.logger
        )
        self.converter = AzElConverter(self)
        self.create_converter_obj_and_antenna_obj()
        self.download_iers_data()

    def create_converter_obj_and_antenna_obj(
        self: DishlnPointingDataComponentManager,
    ):
        """Create AzElConverter Object and antenna object"""
        # Once SKB-398 is fixed from TelModel then this
        # exception handling can be removed.
        try:
            self.converter.create_antenna_obj()
            self.logger.debug("Antenna object created")
        except Exception as exp:
            self.logger.exception("Error while creating antenna obj %s", exp)

    def download_iers_data(self: DishlnPointingDataComponentManager) -> None:
        """Downloads and initialises the IERS file.
        Incase of error with main link, tries downloading using Mirror link.

        :return: None
        :rtype: None
        """
        try:
            self.iers_a = iers.IERS_A.open(iers.IERS_A_URL)
        except Exception as exception:
            self.logger.exception(
                "Failed to download IERS_A data: %s. Trying with a different"
                + " source.",
                exception,
            )
            self.download_iers_data_from_a_different_source()
        self.logger.info("IERS data download completed.")

    
    def download_iers_data_from_a_different_source(
        self: DishlnPointingDataComponentManager,
    ) -> None:
        """Downloads and initialises the IERS file from the mirror or local
        links.

        :return: None
        :rtype: None
        """
        try:
            self.iers_a = iers.IERS_A.open(iers.IERS_A_URL_MIRROR)
        except Exception as exception:
            self.logger.exception(
                "Failed to download IERS_A data: %s. Will use the locally "
                + "stored data.",
                exception,
            )
            self.iers_a = iers.IERS_A.open(IERS_DATA_STORAGE_PATH)

    def update_program_track_table(
        self: DishlnPointingDataComponentManager, program_track_table: List
    ) -> None:
        """
        This method writes the programTrackTable attribute on dish master
        device.

        :param program_track_table: It a list of TAI time, Az and El for
            expected number of TAI times (TrackTableEntries).
        :type program_track_table: list
        :return: None
        :rtype: None
        """

        self.logger.debug(
            "ProgramTrackTable will be updated, "
            "will acquire tango lock for same"
        )
        try:
            self.logger.debug("Acquired  tango lock")
            self.dish_adapter.programTrackTable = program_track_table
            self.logger.debug("ProgramTrackTable Updated")
        except BaseException as exception:
            message = "Exception while writing tracktable: %s" + str(
                exception
            )
            self.logger.exception(message)
            raise Exception(message) from exception
        self.logger.debug("ProgramTrackTable: %s", program_track_table)
    

    def track_process(
        self: DishlnPointingDataComponentManager,
    ) -> None:
        """
        This method manages calculation and writing of programTrackTable
        attribute on DishMaster at the required frequency.

        :return: None
        :rtype: None
        """
        try:
            self.logger.info(
                "ProgramTrackTable generation started.",
            )
            timestamp: Time = Time(datetime.datetime.utcnow(), scale="utc")
            # This is dummy calculation because first time calculation takes
            # time due to IERS file downloads
            if isinstance(self.target_data, str):
                self.converter.point_to_body(self.target_data, timestamp)
            else:
                ra, dec = self.target_data
                self.converter.point(ra, dec, timestamp)

            self.logger.debug("Converter Object Updated")
            utc_now = datetime.datetime.utcnow()

            # For future timestamp few seconds are added in current time.
            # Divided by 1000 to convert ms to sec conversion.
            time_to_add: float = (
                (self.track_table_entries * self.pointing_calculation_period)
                / 1000
            ) + self.track_table_advance_sec

            extended_time: datetime.datetime = utc_now + datetime.timedelta(
                seconds=time_to_add
            )
            self.track_table_calculator.track_table_time_stamp = extended_time
            while self.get_track_process_event_status() is False:
                program_track_table: list = (
                    self.track_table_calculator.calculate_program_track_table(
                        self.target_data, self.converter
                    )
                )
                first_entry_timestamp: float = program_track_table[0]

                # advance_time is subtracted to provide programTrackTable few
                # seconds in advance
                actual_time = (
                    first_entry_timestamp - self.track_table_advance_sec
                )

                scheduled_time = Time(
                    float(actual_time) + Time(SKA_EPOCH, scale="utc").unix_tai,
                    format="unix_tai",
                    scale="tai",
                ).unix

                # Convert to human-readable format
                actual_time_readable = datetime.datetime.utcfromtimestamp(
                    actual_time
                ).strftime("%Y-%m-%d %H:%M:%S")
                scheduled_time_readable = datetime.datetime.utcfromtimestamp(
                    scheduled_time
                ).strftime("%Y-%m-%d %H:%M:%S")

                self.logger.debug("actual_time_human %s", actual_time_readable)
                self.logger.debug(
                    "scheduled_time_human  %s", scheduled_time_readable
                )

                event_priority: int = 1
                self.track_table_scheduler.enterabs(
                    scheduled_time,
                    event_priority,
                    self.update_program_track_table,
                    argument=(program_track_table,),
                )

                self.logger.debug(
                    "update_program_track_table - Added in scheduler"
                )
                self.track_table_scheduler.run()
                self.logger.debug("Execution done")

            self.logger.debug("Program Track Table Calculation stopped.")

            with self.tango_operation_execution_lock:
                self.logger.debug("Grabbed tango operation lock")
                self.dish_adapter.programTrackTable = []

            self.logger.debug("Cleared programTrackTable attribute.")

        except ValueError as value_error:
            self.logger.error("Exception is: %s", str(value_error))
            self.current_track_table_error = [str(value_error)]

        except BaseException as exception:
            self.logger.error(
                "Exception occurred during track_process :%s",
                str(exception),
            )
            self.current_track_table_error = [str(exception)]
