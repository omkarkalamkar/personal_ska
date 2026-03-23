"""
This module provides an implementation of the Dish Leaf Node
pointing device component manager.
"""
from __future__ import annotations

import datetime
import json
import operator
import re
import sched
import threading
import time
from collections import defaultdict
from logging import Logger
from queue import Queue
from typing import Callable, List, Optional, Tuple

import tango
from astropy.time import Time
from astropy.utils import iers
from ska_control_model import TaskStatus
from ska_tango_base.base import TaskCallbackType
from ska_tmc_common.v2.tmc_component_manager import TmcLeafNodeComponentManager

from ska_dishln_pointing_device.commands.generate_program_track_table import (
    GenerateProgramTrackTable,
)
from ska_dishln_pointing_device.event_manager import DishLNPDEventManager
from ska_tmc_dishleafnode.az_el_converter import (
    AzElConverter_v2 as AzElConverter,
)
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
        entries_tt_schedular_queue: int = 5,
        _event_manager: bool = False,
        weather_station_device_names: Optional[list] = None,
        event_subscription_check_period: int = 1,
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
        self.event_manager = _event_manager
        self.target: list | str | None = None
        self.antenna_target = None
        self.projection_name: str = "SIN"
        self.projection_alignment = "AltAz"
        self.fixed_x_offset: float = 0.0
        self.fixed_y_offset: float = 0.0
        self.projection_and_fixed_trajectory_data = []
        self._current_track_table_error = ""
        self.__target_data: dict = {}
        # This event can be used by on going process to change the offset
        # and clear the event for next usage.
        self.mapping_scan_event = threading.Event()
        self.set_change_pointing_event = threading.Event()
        self.elevation_max_limit = elevation_max_limit
        self.elevation_min_limit = elevation_min_limit
        self._array_layout = {}
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
            target=self.download_antenna_and_iers_data, daemon=True
        )
        self.data_download_thread.start()
        self.track_thread_lock = threading.RLock()
        self.track_table_thread = None
        self._wrap_sector: int
        self._wrap_sector_key: bool = False
        self.__humidity: float = 0.10
        self.__pressure: float = 900.0
        self.__wind_speed: float = 10.0
        self.__temperature: float = 30.0
        self.entries_tt_schedular_queue = entries_tt_schedular_queue
        self.weather_station_device_name: str = ""
        if weather_station_device_names:
            self.weather_station_device_name = weather_station_device_names[0]
        self.event_processing_methods = self.get_attribute_dict()
        self.event_threads: list[threading.Thread] = []
        self.event_manager_object: DishLNPDEventManager = DishLNPDEventManager(
            self,
            logger=logger,
            event_subscription_check_period=event_subscription_check_period,
        )
        self.start_event_processing_threads()
        self.setup_event_subscription()
        self.stop_track_called: threading.Event = threading.Event()

    def start_event_processing_threads(self) -> None:
        """Start all the event processing threads."""
        # reset flag and any previous threads
        self._stop_thread = False
        self.event_threads.clear()

        for attribute, _ in self.event_processing_methods.items():
            self.event_queues[attribute] = Queue()
            thread = threading.Thread(
                target=self.process_event,
                args=[attribute],
                name=f"evt_{attribute}",
            )
            self.event_threads.append(thread)
            thread.start()

    def process_event(self, attribute_name):
        with tango.EnsureOmniThread():
            super().process_event(attribute_name)

    def stop_event_processing_threads(self) -> None:
        """
        Stop all event-processing threads:
        1) Signal them to exit their loops.
        2) Wait (join) until each thread has terminated.
        3) Clean up queues and thread list.
        """
        # signal all threads to stop
        self._stop_thread = True

        # join each thread so we wait for their clean exit
        for thread in self.event_threads:
            if thread.is_alive():
                thread.join()

        # optionally clear queues and thread references
        self.event_queues.clear()
        self.event_threads.clear()

        # reset flag so you can restart later if needed
        self._stop_thread = False

    # pylint: disable-next=unused-argument
    def check_device_responsiveness(self, device_name: str) -> bool:
        """This method accepts device_name and
        provides the responsiveness of the device.

        :param device_name: Tango device FQDN.
        :type device_name: str
        :raises DeviceNameIncorrect: raises exception when
            device name is incorrect.
        :return: Returns True when device is avaiable, else false.
        :rtype: bool
        """
        return True

    @property
    def humidity(self) -> float:
        """The humidity property."""
        return self.__humidity

    @humidity.setter
    def humidity(self, humidity: float) -> None:
        """The setter for humidity property."""
        with self.rlock:
            self.__humidity = humidity

    @property
    def pressure(self) -> float:
        """The pressure property."""
        return self.__pressure

    @pressure.setter
    def pressure(self, pressure: float) -> None:
        """The setter for pressure property."""
        with self.rlock:
            self.__pressure = pressure

    @property
    def wind_speed(self) -> float:
        """The wind speed property."""
        return self.__wind_speed

    @wind_speed.setter
    def wind_speed(self, wind_speed: float) -> None:
        """The setter for wind_speed property."""
        with self.rlock:
            self.__wind_speed = wind_speed

    @property
    def temperature(self) -> float:
        """The temperature property."""
        return self.__temperature

    @temperature.setter
    def temperature(self, temperature: float) -> None:
        """The setter for temperature property."""
        with self.rlock:
            self.__temperature = temperature

    def setup_event_subscription(self) -> None:
        """
        Sets up the event subscription after input parameters are updated.
        """

        self.start_event_manager(
            self.build_device_attribute_map(), timeout=1000
        )
        self.logger.debug("Successfully subscribed to the events.")

    def build_device_attribute_map(self) -> dict[str, list[str]]:
        """
        Builds a dictionary mapping device names to lists of attributes
        to be subscribed.

        Returns:
            Dict[str, List[str]]: A mapping from device names to list of
            attributes.
        """
        device_attribute_map = defaultdict(list)

        if self.weather_station_device_name:
            device_attribute_map[self.weather_station_device_name] = [
                "humidity",
                "temperature",
                "windSpeed",
                "pressure",
            ]

        self.logger.debug(
            "Device attribute map dictionary : %s", device_attribute_map
        )
        return device_attribute_map

    @property
    def wrap_sector_key(self: DishlnPointingDataComponentManager) -> bool:
        """Get the pointing key type

        Returns:
            bool:
                - True => ['pointing']['groups'] as per ADR-106
                - False => ['pointing']['target'] old or deprecated
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

    @property
    def array_layout(self) -> dict:
        """Returns the array layout"""
        return dict(self._array_layout)

    # DishlnPointingDataComponentManager.array_layout.setter
    @array_layout.setter
    def array_layout(self, layout: dict | str) -> None:
        """Sets the array layout
        :param layout: The array layout to set
        :type layout: dict | str
        :return: None"""
        if isinstance(layout, str):
            layout = json.loads(layout)
        if dict(self._array_layout) != layout:
            self._array_layout.clear()
            self._array_layout.update(layout)
            self.logger.info("array_layout updated.")
            # NEW: (re)create antenna & set observer now that layout exists
            try:
                self.converter.create_antenna_obj()
                if self.observer is None:
                    self.logger.warning(
                        "Observer is still None after layout update."
                    )
            except Exception as e:
                self.logger.exception(
                    "Failed to build observer from layout: %s", e
                )

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
            dict: Dictionary of configure data
        """
        return self.__target_data

    @target_data.setter
    def target_data(self: DishlnPointingDataComponentManager, data: dict):
        """This method is used to update target data.

        Args:
            data (str): pointing data from configure command.
        """
        try:
            self.logger.info("target data is: %s", data)
            self.__target_data = data
            # Set the wrap key
            self.set_wrap_sector_data()

            # NEW: rebuild observer if layout is supplied
            layout = self.__target_data.get("array_layout")
            if layout is not None:
                self.array_layout = layout
                try:
                    self.converter.create_antenna_obj()
                    self.logger.debug(
                        "Observer rebuilt from received array_layout."
                    )
                except Exception as exp:
                    self.logger.exception(
                        "Failed to rebuild observer: %s", str(exp)
                    )
        except Exception as exception:
            self.logger.exception(
                "Failed to update target data due to exception: %s",
                exception,
            )

    @property
    def current_track_table_error(
        self: DishlnPointingDataComponentManager,
    ) -> str:
        """Gets the trackTableError of the dish leaf node.

        Returns:
            str: trackTableError of the dish leaf node.
        """
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
        with tango.EnsureOmniThread():
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
                # added condition for edge case where tracktable start
                # and stop are running parallely.
                if not self.stop_track_called.is_set():
                    # clear mapping scan event to start new thread
                    self.mapping_scan_event.clear()
                    self.create_track_table_thread()
                    self.track_table_thread.start()

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
            pre_entries_of_ptt_in_schedular = self.entries_tt_schedular_queue
            self.logger.debug(
                "Starting ProgramTrackTable calculation.",
            )
            timestamp: Time = Time(datetime.datetime.utcnow(), scale="utc")
            self.converter.point(timestamp)
            self.update_program_track_table_error_callback("")

            utc_now = datetime.datetime.utcnow()

            # The average time required to perform a
            # RaDec to AzEl conversion
            # is approximately 20 milliseconds. Therefore, the total
            # calculation time and the advanced
            #  tracktable time are added to
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
            track_table_calculator.track_table_scheduler = (
                track_table_scheduler
            )
            while not is_track_thread_stop:
                self.logger.debug(
                    "Target used to calculate trackTable: %s "
                    "with thread id: %s",
                    self.target,
                    threading.get_native_id(),
                )

                with self.track_thread_lock:
                    is_track_thread_stop = self.mapping_scan_event.is_set()
                program_track_table: list = (
                    track_table_calculator.calculate_program_track_table(
                        azel_converter=self.converter,
                    )
                )

                first_entry_timestamp: float = program_track_table[0]

                # advance_time is subtracted to provide
                #  programTrackTable few
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

                self.logger.debug(
                    "Actual Time: %s, Scheduled time: %s",
                    actual_time_readable,
                    scheduled_time_readable,
                )

                with self.track_thread_lock:
                    if not self.mapping_scan_event.is_set():
                        if pre_entries_of_ptt_in_schedular > 0:
                            pre_entries_of_ptt_in_schedular -= 1
                        else:
                            track_table_calculator.ptt_buffer_set = True
                        track_table_scheduler.enterabs(
                            scheduled_time,
                            event_priority,
                            self.update_pointing_program_track_table,
                            argument=(program_track_table,),
                        )
                        self.logger.debug(
                            "Scheduled trackTable write operation with "
                            "scheduler Length: %s",
                            len(track_table_scheduler.queue),
                        )

            self.logger.debug("Program trackTable calculation stopped.")
        except Exception as value_error:
            self.logger.error(
                "Error occurred during track_thread execution: %s",
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

    def generate_program_track_table(
        self, task_callback: TaskCallbackType, task_abort_event=None
    ) -> Tuple[TaskStatus, str]:
        """
        Submit GenerateProgramTrackTable as a long-running background task.

        Args:
            task_callback (TaskCallbackType): A callback used to monitor
            or update task progress.

        Returns:
            Tuple[TaskStatus, str]: The final status of the
            task and a status message.
        """
        command_object = GenerateProgramTrackTable(
            component_manager=self,
            logger=self.logger,
        )

        return command_object.generate_program_track_table(
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

    def update_windspeed(self, wind_speed: float) -> None:
        """The method to update windspeed

        :param wind_speed: the wind speed event from wms.
        :type wind_speed: float
        """
        if wind_speed:
            self.wind_speed = wind_speed

    def update_temperature(self, temperature: float) -> None:
        """The method to update temperature

        :param temperature: The temperature event from wms.
        :type temperature: float
        """
        if temperature:
            self.temperature = temperature

    def update_pressure(self, pressure: float) -> None:
        """The method to update pressure.

        :param pressure: The pressure event from the wms.
        :type pressure: float
        """
        if pressure:
            self.pressure = pressure

    def update_humidity(self, humidity: float) -> None:
        """The method to update humidity.

        :param humidity: The humidity event from the wms.
        :type humidity: float
        """
        if humidity:
            self.humidity = humidity

    def check_event_error(self, event: tango.EventData, callback: str):
        """Method for checking event error."""
        if event.err:
            error = event.errors[0]
            self.logger.error(
                "Error occurred on %s for device: %s - %s, %s",
                callback,
                event.device.dev_name(),
                error.reason,
                error.desc,
            )
            return True
        return False

    def get_attribute_dict(self) -> dict:
        """
        This method will return dictionary of attributes which will
        be subscribed by TMC Dish Leaf Node Pointing Device.
        It will contain mapping of attribute with function which will
        process event data in TMC

        :return: Dictionary of attributes to be handled by the EventReceiver.
        """

        attributes = {
            "windSpeed": self.update_windspeed,
            "pressure": self.update_pressure,
            "humidity": self.update_humidity,
            "temperature": self.update_temperature,
        }
        return {**attributes}
