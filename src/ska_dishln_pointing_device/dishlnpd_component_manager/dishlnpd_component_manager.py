"""
This module provides an implementation of the Dish Leaf Node
pointing device component manager.
"""
from __future__ import annotations

import datetime
import operator
import re
import sched
import threading
import time
from logging import Logger
from typing import Callable, List, Optional, Tuple

from astropy.time import Time
from astropy.utils import iers
from ska_tango_base.commands import TaskStatus
from ska_tmc_common import DishMode
from ska_tmc_common.v1.tmc_component_manager import TmcLeafNodeComponentManager

from ska_dishln_pointing_device.commands.generate_program_track_table import (
    GenerateProgramTrackTable,
)
from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.constants import (
    IERS_DATA_STORAGE_PATH,
    PROGRAM_TRACK_TABLE_SIZE,
    SKA_EPOCH,
)
from ska_tmc_dishleafnode.manager.program_track_table_calculator import (
    ProgramTrackTableCalculator,
)


class DishlnPointingDataComponentManager(TmcLeafNodeComponentManager):
    """
    A component manager for The Dish leaf node pointing device component.
    """

    def __init__(
        self,
        disln_pointing_device_name: str,
        logger: Logger,
        update_pointing_program_track_table_callback: Callable,
        update_program_track_table_error_callback: Callable,
        track_table_update_rate: float,
        elevation_max_limit: float = 90.0,
        elevation_min_limit: float = 15.0,
        track_table_advance_sec: int = 6,
        azimuth_min_limit: float = -270.0,
        azimuth_max_limit: float = 270.0,
    ):
        """
        Initialise a new ComponentManager instance.

        :param logger: a logger for this component manager
        :param dishln_pointing_device_name: name of the dish
            pointing device
        """

        super().__init__(logger)
        self.logger = logger
        self.pointing_program_track_table: list = []
        self.update_pointing_program_track_table_callback = (
            update_pointing_program_track_table_callback
        )
        self.update_program_track_table_error_callback = (
            update_program_track_table_error_callback
        )
        self.target: list | str | None = None
        self._current_track_table_error = ""
        self.__target_data: dict = {}
        # This event can be used by on going process to change the offset
        # and clear the event for next usage.
        self.mapping_scan_event = threading.Event()
        self.set_change_pointing_event = threading.Event()
        self.elevation_max_limit = elevation_max_limit
        self.elevation_min_limit = elevation_min_limit
        self.azimuth_min_limit = azimuth_min_limit
        self.azimuth_max_limit = azimuth_max_limit
        self.iers_a = None
        self.observer = None
        self.track_table_update_rate: float = track_table_update_rate
        self.track_table_advance_sec: float = track_table_advance_sec
        self.dishln_pointing_device_name = disln_pointing_device_name
        self.logger.info(
            "Dish leaf node pointing device name is: %s",
            self.dishln_pointing_device_name,
        )
        self.dish_id = re.findall(
            "\\b(?:SKA|MKT)\\d{3}\\b",
            self.dishln_pointing_device_name,
            flags=re.IGNORECASE,
        )[0]
        self.current_mapping_scan_obj = None
        self.converter = AzElConverter(self)
        self.data_download_thread = threading.Thread(
            target=self.download_antenna_and_iers_data
        )
        self.data_download_thread.start()
        self.track_thread_lock = threading.RLock()
        self.track_table_thread = None
        self._wrap_sector: int
        self._wrap_sector_key: bool = False

    @property
    def wrap_sector_key(self: DishlnPointingDataComponentManager) -> bool:
        """Get the pointing key type
            True => ['pointing']['groups'] as per ADR-106
            False => ['pointing']['target'] old or deprecated

        Returns:
            boolean value.
        """
        return self._wrap_sector_key

    @wrap_sector_key.setter
    def wrap_sector_key(
        self: DishlnPointingDataComponentManager, value: bool
    ) -> None:
        """
        Set the pointing key type
            True => ['pointing']['groups'] as per ADR-106
            False => ['pointing']['target'] old or deprecated

        :param value:
        :type value: boolean
        :return: None
        :rtype: None
        """
        self._wrap_sector_key = value

    @property
    def wrap_sector(self: DishlnPointingDataComponentManager) -> int:
        """Get the wrap sector value
        :return: wrap sector value
        :rtype: int
        """
        return self._wrap_sector

    @wrap_sector.setter
    def wrap_sector(
        self: DishlnPointingDataComponentManager, wrap_sector: int
    ) -> None:
        """Set the wrap sector
        :param wrap_sector:
        :type wrap_sector: int
        :return: None
        :rtype: None
        """
        self._wrap_sector = wrap_sector

    @property
    def target_data(self: DishlnPointingDataComponentManager) -> dict:
        """This method is used to view target data.
        Returns:
            Dictionary of configure data
        """
        return self.__target_data

    @target_data.setter
    def target_data(self: DishlnPointingDataComponentManager, data: dict):
        """This method is used to update target data.

        Args:
            data (str): pointing data from configure command.
        """
        try:
            self.__target_data = data
            # Set the wrap key
            self.set_wrap_sector_data()
        except Exception as exception:
            self.logger.exception(
                "Failed to update target data due to exception: %s",
                exception,
            )

    @property
    def current_track_table_error(self: DishlnPointingDataComponentManager):
        """Returns the trackTableError of the dish leaf node."""
        return self._current_track_table_error

    @current_track_table_error.setter
    def current_track_table_error(
        self: DishlnPointingDataComponentManager, value: str
    ) -> None:
        """Update the trackTableError of the dish leaf node
        :param value: Error observed in track table calculation
        :value dtype: str
        :return: None
        :rtype: None
        """
        self._current_track_table_error = value

    def is_fixed_mapping_scan(self) -> bool:
        """Method to check is current scan is fixed mapping scan
        :return: True/False
        :rtype: boolean
        """
        if (
            self.target_data.get("pointing", {})
            .get("trajectory", {})
            .get("name", "")
            .lower()
            == "fixed"
        ):
            return True
        return False

    def set_wrap_sector_data(self) -> None:
        """
        Set the wrap sector for the observation

        Returns:
            None
        """
        if "wrap_sector" in self.target_data.get("pointing", {}):
            self.wrap_sector_key = True
            self.wrap_sector = self.target_data["pointing"]["wrap_sector"]
            self.logger.info(
                "Wrap sector set to: %s",
                self.wrap_sector,
            )

    def download_antenna_and_iers_data(self):
        """Method that downloads antenna and iers data"""
        self.create_converter_obj_and_antenna_obj()
        self.download_iers_data()

    def create_converter_obj_and_antenna_obj(
        self: DishlnPointingDataComponentManager,
    ):
        """Create AzElConverter Object and antenna object"""

        self.converter.create_antenna_obj()
        self.logger.debug(
            "Antenna object created for %s",
            self.dishln_pointing_device_name,
        )

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
                "Failed to download IERS_A data due to exception: %s."
                + "Trying with Mirror link",
                str(exception),
            )
            self.download_iers_data_from_a_different_source()
        self.logger.info("IERS data download completed.")

    def clear_track_table_errors(self):
        """Clear track table errors"""
        self.current_track_table_error = ""
        self.update_program_track_table_error_callback("")

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
                "Failed to download IERS_A data due to exception: %s."
                + " Use local or mirror IERS file",
                str(exception),
            )
            self.iers_a = iers.IERS_A.open(IERS_DATA_STORAGE_PATH)

    def update_pointing_program_track_table(
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
        try:
            self.pointing_program_track_table = program_track_table
            self.update_pointing_program_track_table_callback(
                self.pointing_program_track_table
            )
        except BaseException as exception:
            message = "Exception while writing trackTable: %s" + str(exception)
            self.logger.exception(message)
            raise Exception(message) from exception
        self.logger.debug(
            "Calculated ProgramTrackTable: %s",
            program_track_table,
        )

    def stop_track_table_thread(self):
        """Stop the track table thread if it is running"""
        with self.track_thread_lock:
            self.mapping_scan_event.set()
        if self.track_table_thread and self.track_table_thread.is_alive():
            self.track_table_thread.join()
            self.logger.debug("Track Table thread stopped")

    def start_track_table_calculation(self) -> None:
        """This method creates and starts a thread for the programTrackTable
        calculation."""
        try:
            # Stop existing thread if alive
            self.stop_track_table_thread()
            with self.track_thread_lock:
                # clear mapping scan event to start new thread
                self.mapping_scan_event.clear()
                self.create_track_table_thread()
                self.track_table_thread.start()
                self.logger.debug("Started trackTable thread.")
        except Exception as exception:
            self.logger.exception(
                "Failed to start trackTable thread" + " due to exception: %s",
                str(exception),
            )

    def create_track_table_thread(self) -> None:
        """This creates thread for track table calculation."""
        try:
            self.track_table_thread = threading.Thread(
                target=self.track_thread
            )
        except Exception as exception:
            self.logger.exception(
                "Failed to create trackTable thread "
                + " due to exception: %s ",
                str(exception),
            )

    def track_thread(
        self: DishlnPointingDataComponentManager,
    ) -> None:
        """
        This method manages calculation and writing of programTrackTable
        attribute on DishMaster at the required frequency.

        :return: None
        :rtype: None
        """
        try:
            self.logger.debug(
                "Starting ProgramTrackTable calculation.",
            )
            timestamp: Time = Time(datetime.datetime.utcnow(), scale="utc")
            # This is dummy calculation because first time calculation takes
            # time due to IERS file downloads
            if isinstance(self.target, str):
                self.converter.point_to_body(self.target, timestamp)
            else:
                ra, dec = self.target  # pylint: disable=E0633
                self.converter.point(ra, dec, timestamp)

            self.update_program_track_table_error_callback("")
            self.logger.debug("Converter Object Updated")

            utc_now = datetime.datetime.utcnow()

            # The average time required to perform a RaDec to AzEl conversion
            # is approximately 20 milliseconds. Therefore, the total
            # calculation time and the advanced tracktable time are added to
            # the current timestamp to generate the future tracktable.

            RaDec_AzEl_conversion_time = 0.02
            time_to_add: float = (
                operator.mul(
                    PROGRAM_TRACK_TABLE_SIZE, RaDec_AzEl_conversion_time
                )
                + self.track_table_advance_sec
            )

            extended_time: datetime.datetime = utc_now + datetime.timedelta(
                seconds=time_to_add
            )
            track_table_calculator = ProgramTrackTableCalculator(
                self, self.logger
            )
            track_table_calculator.track_table_time_stamp = extended_time

            with self.track_thread_lock:
                is_track_thread_stop = self.mapping_scan_event.is_set()

            track_table_scheduler = sched.scheduler(time.time, time.sleep)
            event_priority: int = 1
            while not is_track_thread_stop:
                self.logger.debug(
                    "Current Thread ID: %s", threading.get_native_id()
                )
                self.logger.debug(
                    "Target used to calculate trackTable: %s", self.target
                )

                with self.track_thread_lock:
                    is_track_thread_stop = self.mapping_scan_event.is_set()
                program_track_table: list = (
                    track_table_calculator.calculate_program_track_table(
                        self.target, self.converter
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

                self.logger.debug("Actual Time: %s", actual_time_readable)
                self.logger.debug(
                    "Scheduled time: %s", scheduled_time_readable
                )

                with self.track_thread_lock:
                    if not self.mapping_scan_event.is_set():
                        track_table_scheduler.enterabs(
                            scheduled_time,
                            event_priority,
                            self.update_pointing_program_track_table,
                            argument=(program_track_table,),
                        )
                        self.logger.debug(
                            "Scheduled trackTable write operation"
                        )
                        track_table_scheduler.run(blocking=False)
                        self.logger.debug("Schedular execution completed")

            self.logger.debug("Program TrackTable Calculation stopped.")

        except Exception as value_error:
            self.logger.error(
                "Error occured during track_thread execution: %s",
                str(value_error),
            )
            self.update_program_track_table_error_callback(str(value_error))
            self.current_track_table_error = str(value_error)

        except BaseException as exception:
            self.logger.exception(
                "Exception occurred during track_thread :%s",
                str(exception),
            )
            self.update_program_track_table_error_callback(str(exception))
            self.current_track_table_error = str(exception)

    # def is_command_allowed_callable(
    #     self: DishlnPointingDataComponentManager, command_name: str
    # ):
    #     """
    #     Args:
    #         command_name (str): Name for the command for which the is_allowed
    #             check need to be applied.
    #     """
    #     self.check_device_responsive()

    #     def check_dish_mode():
    #         """Return whether the command may be called in the current state.

    #         Returns:
    #             bool: whether the command may be called in the current device
    #             state
    #         """

    #     return check_dish_mode

    def is_command_allowed_callable(
        self: DishlnPointingDataComponentManager, command_name: str
    ):
        """
        Returns a callable that determines whether the given command is allowed
        based on the component manager's internal state.

        Args:
            command_name (str): Name of the command to check.

        Returns:
            Callable[[], bool]: A function that returns True if the
            command is allowed.
        """

        def check_dish_mode() -> bool:
            """Determine if the command is allowed based on
            current dish state."""

            allowed_modes = [DishMode.OPERATE]

            current_mode = getattr(self, "dishMode", None)
            self.logger.info(current_mode)
            self.logger.info(command_name)
            self.logger.info(allowed_modes)
            return (
                # True
                command_name == "GenerateProgramTrackTable"
                and current_mode in allowed_modes
            )

        return check_dish_mode

    def generate_program_track_table(
        self, task_callback: Optional[Callable] = None
    ) -> Tuple[TaskStatus, str]:
        """
        Submit GenerateProgramTrackTable as a long-running background task.

        :param task_callback: Callback for tracking status
        :return: TaskStatus and message
        """
        self.logger.info(
            "Submitting GenerateProgramTrackTable as slow command"
        )

        command = GenerateProgramTrackTable(
            component_manager=self,
            logger=self.logger,
        )

        return self.submit_task(
            command.generate_program_track_table,
            task_callback=task_callback,
            is_cmd_allowed=self.is_command_allowed_callable(
                "GenerateProgramTrackTable"
            ),
        )
