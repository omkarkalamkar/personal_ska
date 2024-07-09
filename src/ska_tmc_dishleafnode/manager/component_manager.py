"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
import datetime
import json
import math
import os
import re
import sched
import threading
import time
from logging import Logger
from multiprocessing import Event, Lock, Manager, Process, current_process
from typing import Callable, List, Tuple, Union

import numpy as np
import tango
from astropy.utils import iers
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import (
    AdapterFactory,
    Band,
    CommandNotAllowed,
    DeviceInfo,
    DeviceUnresponsive,
    DishDeviceInfo,
    DishMode,
    LivelinessProbeType,
    PointingState,
    SdpQueueConnectorDeviceInfo,
    TmcLeafNodeComponentManager,
)
from ska_tmc_common.adapters import DishAdapter

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.commands import (
    Configure,
    EndScan,
    Off,
    Scan,
    SetOperateMode,
    SetStandbyFPMode,
    SetStandbyLPMode,
    SetStowMode,
    Track,
    TrackLoadStaticOff,
    TrackStop,
)

from .dish_kvalue_validation_manager import DishkValueValidationManager
from .event_receiver import DishLNEventReceiver
from .program_track_table_calculator import ProgramTrackTableCalculator


class DishLNComponentManager(TmcLeafNodeComponentManager):
    """
    A component manager for The Dish Leaf Node component.
    """

    # pylint: disable=unused-argument
    def __init__(
        self,
        dish_dev_name: str,
        logger: Logger,
        track_table_entries: int,
        pointing_calculation_period: int,
        _update_dishmode_callback: Callable,
        _update_pointingstate_callback: Callable,
        communication_state_callback: Callable,
        component_state_callback: Callable,
        pointing_callback: Callable,
        kvalue_validation_callback: Callable,
        _update_availablity_callback: Callable,
        _update_source_offset_callback: Callable,
        _update_last_pointing_data_cb: Callable,
        _liveliness_probe=LivelinessProbeType.SINGLE_DEVICE,
        _event_receiver: bool = True,
        proxy_timeout: int = 500,
        sleep_time: int = 1,
        dish_availability_check_timeout: int = 40,
        command_timeout: int = 15,
        is_dish_abort_commands: bool = False,
        adapter_timeout: int = 2,
        elevation: float = 0.0,
        azimuth: float = 0.0,
        elevation_max_limit: float = 0.0,
        elevation_min_limit: float = 0.0,
    ):
        """
        Initialise a new ComponentManager instance.

        :param logger: a logger for this component manager
        :param liveliness_probe: allows enabling/disabling the
            liveliness probe
        :param component_state_callback: callback to be called
            when state of the component changed
        :param communication_state_callback: callback to be called
            when communication status of the component changed
        :param event_receiver: flag used to control whether
            EventReceiver object should be instantiated or not
        :param proxy_timeout: allows to specify a client side timeout
            for sub-devices in milliseconds used by the liveliness probe
        :param sleep_time: allows to specify the wait between
            each iteration of the liveliness probe and EventSubscriber
        :param timeout: Time period to wait for initialization
            of adapter
        """
        super().__init__(
            logger=logger,
            _liveliness_probe=_liveliness_probe,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            proxy_timeout=proxy_timeout,
            sleep_time=sleep_time,
        )
        self._device = DishDeviceInfo(dish_dev_name)
        self.logger = logger
        __adapter_factory = AdapterFactory()
        self.command_timeout = command_timeout
        self.adapter_timeout = adapter_timeout
        self.dish_dev_name = dish_dev_name
        self.dish_id = (
            re.findall(
                "\\b(?:SKA|MKT)\\d{3}\\b", dish_dev_name, flags=re.IGNORECASE
            )[0]
            if dish_dev_name
            else None
        )
        self.tango_operation_execution_lock = Lock()
        self.observer = None
        self.dish_number = None
        self._track_process_event = Event()
        self.reset_track_process_event()
        self.elevation = elevation
        self.azimuth = azimuth
        self.elevation_max_limit = elevation_max_limit
        self.elevation_min_limit = elevation_min_limit
        self.el_limit = False
        self.is_dish_abort_commands = is_dish_abort_commands
        self.radec_value = ""
        self.process_manager = Manager()
        self._actual_pointing = self.process_manager.list()
        self.pointing_callback = pointing_callback
        self._update_dishmode_callback = _update_dishmode_callback
        self._update_pointingstate_callback = _update_pointingstate_callback
        self._kvalue: int = 0
        self._kValueValidationResult = ResultCode.STARTED
        self.kvalue_validation_callback = kvalue_validation_callback
        self.dish_availability_check_timeout = dish_availability_check_timeout
        self.iers_a = None
        self.achieved_pointing_data = self.process_manager.Queue()
        self.actual_pointing_process_alive = Event()
        self._queue_connector_device_info: SdpQueueConnectorDeviceInfo = (
            SdpQueueConnectorDeviceInfo()
        )
        self.received_pointing_data = self.process_manager.list(
            [self._queue_connector_device_info]
        )
        self._last_pointing_data = np.array([0.0, 0.0, 0.0])
        self._update_source_offset_callback = _update_source_offset_callback
        self._update_last_pointing_data_callback = (
            _update_last_pointing_data_cb
        )
        self.update_availablity_callback = _update_availablity_callback
        self.supported_commands: Tuple[str, str] = (
            "Configure_TrackLoadStaticOff",
            "TrackLoadStaticOff",
        )
        self.extended_time: int = 0
        self.__command_in_progress: str = ""

        # Event Receiver
        if _event_receiver:
            self.event_receiver_object = DishLNEventReceiver(self, logger)
            self.event_receiver_object.start()

        if _liveliness_probe != LivelinessProbeType.NONE:
            self.start_liveliness_probe(_liveliness_probe)

        self.track_table_scheduler = sched.scheduler(time.time, time.sleep)
        self.dish_adapter: DishAdapter | None = None
        self.track_table_entries = track_table_entries
        self.pointing_calculation_period = pointing_calculation_period
        self.track_table_calculator = ProgramTrackTableCalculator(
            self, self.logger
        )

        self.setstandbyfpmode_command = SetStandbyFPMode(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.setstandbylpmode_command = SetStandbyLPMode(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.setstowmode_command = SetStowMode(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.setoperatemode_command = SetOperateMode(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.configure_command = Configure(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.scan_command = Scan(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.endscan_command = EndScan(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.track_command = Track(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.trackstop_command = TrackStop(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.off_command = Off(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.track_load_static_off_command = TrackLoadStaticOff(
            self,
            self.op_state_model,
            __adapter_factory,
            self.logger,
        )

        self.actual_pointing_process = Process(
            target=self.process_actual_pointing,
        )
        self.command_object: dict = {
            "TrackLoadStaticOff": self.track_load_static_off_command,
            "Configure_TrackLoadStaticOff": self.configure_command,
        }
        self.process_lock = Lock()
        self.kvalue_validation_thread = threading.Timer(
            5, self.update_kvalue_validation_result
        )
        self.create_converter_obj_and_antenna_obj()
        self.download_iers_data()
        self.kvalue_validation_thread.start()
        self.actual_pointing_process.start()

    def create_converter_obj_and_antenna_obj(self):
        """Create AzElConverter Object and antenna object"""
        # Once SKB-398 is fixed from TelModel then this
        # exception handling can be removed.
        try:
            self.converter = AzElConverter(self)
            self.converter.create_antenna_obj()
        except Exception as exp:
            self.logger.exception("Error while creating antenna obj %s", exp)

    def is_command_allowed_callable(self, command_name: str):
        """
        Args:
            command_name (str): Name for the command for which the is_allowed
                check need to be applied.
        """
        self.check_device_responsive()

        def check_dish_mode():
            """Return whether the command may be called in the current state.

            Returns:
                bool: whether the command may be called in the current device
                state
            """
            command_allowed_dish_mode = {
                "SetStowMode": [
                    DishMode.STANDBY_FP,
                    DishMode.OPERATE,
                    DishMode.STANDBY_LP,
                    DishMode.CONFIG,
                ],
                "SetStandbyLPMode": [
                    DishMode.STANDBY_FP,
                    DishMode.STOW,
                    DishMode.MAINTENANCE,
                ],
                "Configure": [
                    DishMode.STANDBY_FP,
                    DishMode.STOW,
                    DishMode.OPERATE,
                ],
                "Track": [DishMode.OPERATE],
                "SetStandbyFPMode": [
                    DishMode.STANDBY_LP,
                    DishMode.OPERATE,
                    DishMode.STOW,
                    DishMode.MAINTENANCE,
                ],
                "TrackLoadStaticOff": [
                    DishMode.STANDBY_FP,
                    DishMode.OPERATE,
                    DishMode.STANDBY_LP,
                    DishMode.CONFIG,
                    DishMode.MAINTENANCE,
                    DishMode.STARTUP,
                    DishMode.SHUTDOWN,
                    DishMode.UNKNOWN,
                ],
                "TrackStop": [DishMode.OPERATE],
                "SetOperateMode": [DishMode.STANDBY_FP],
                "Scan": [
                    DishMode.OPERATE,
                    DishMode.STANDBY_FP,
                    DishMode.STOW,
                    DishMode.MAINTENANCE,
                ],
                "EndScan": [
                    DishMode.OPERATE,
                    DishMode.STANDBY_FP,
                    DishMode.STOW,
                    DishMode.MAINTENANCE,
                ],
            }

            allowed_dish_modes = command_allowed_dish_mode.get(
                command_name, []
            )

            return self.dishMode in allowed_dish_modes

        return check_dish_mode

    def is_track_and_trackstop_command_allowed(self):
        """checks if track command is allowed"""
        if self.dishMode == DishMode.OPERATE and self.pointingState not in (
            PointingState.NONE,
            PointingState.UNKNOWN,
        ):
            return True
        return False

    @property
    def kValueValidationResult(self) -> int:
        """Returns the k-value validation result

        :return: The k-value validation result
        :rtype: int
        """

        return self._kValueValidationResult

    @kValueValidationResult.setter
    def kValueValidationResult(self, result_code: ResultCode) -> None:
        """Update the k-value validation result property."""
        if self._kValueValidationResult != result_code:
            self._kValueValidationResult = result_code

    @property
    def kValue(self) -> int:
        """Returns the k-value"""
        return self._kvalue

    @kValue.setter
    def kValue(self, k_value: int) -> None:
        """Update the k-value property."""
        if self._kvalue != k_value:
            self._kvalue = k_value

    @property
    def dishMode(self) -> DishMode:
        """Returns the dishMode of dish master device"""
        return self._device.dish_mode

    @property
    def pointingState(self) -> PointingState:
        """Returns the pointingState of dish master device"""
        return self._device.pointing_state

    @property
    def dishConfiguredBand(self) -> str:
        """Returns the dishConfiguredBand of dish device"""
        return str(self._device.configured_band)

    @property
    def actual_pointing(self) -> list:
        """Returns the actualPointing of the dish device."""
        return list(self._actual_pointing)

    @property
    def command_in_progress(self) -> str:
        """Method to get value of current command in progress

        return: command in progress variable data
        rtype: str
        """
        return self.__command_in_progress

    @property
    def queue_connector_device_info(self) -> SdpQueueConnectorDeviceInfo:
        """Get the queue connector device object"""
        return self._queue_connector_device_info

    @command_in_progress.setter
    def command_in_progress(self, cmd_in_progress: str) -> None:
        """Method used to set command in progress value.

        :param cmd_in_progress (str): Name of current command in progress

        :return: None
        """
        self.__command_in_progress = cmd_in_progress

    @actual_pointing.setter
    def actual_pointing(self, value: list) -> None:
        """Update the actualPointing of the dish device.

        :param value: The list containing timestamp, RA and Dec values.
        :value dtype: List
        :return: None
        :rtype: None
        """
        self._actual_pointing[:] = value
        self.logger.info(
            "The updated actual pointing values are: %s", self._actual_pointing
        )
        if self.pointing_callback:
            self.pointing_callback(list(self._actual_pointing))

    @property
    def last_pointing_data(self):
        """Property for last pointing data"""
        return self._last_pointing_data

    @last_pointing_data.setter
    def last_pointing_data(self, last_pointing_data) -> None:
        """Method to update the lastPointingData attribute"""
        self._last_pointing_data = last_pointing_data
        with self.lock:
            if self._update_last_pointing_data_callback:
                self._update_last_pointing_data_callback(last_pointing_data)

    def update_source_offset_callback(self, source_offset: list) -> None:
        """Method to update the sourceOffset attribute"""
        with self.lock:
            if self._update_source_offset_callback:
                self._update_source_offset_callback(source_offset)

    def download_iers_data(self) -> None:
        """Downloads and initialises the IERS file.
        Incase of error with main link, tries downloading using Mirror link.

        :return: None
        :rtype: None
        """
        try:
            self.iers_a = iers.IERS_A.open(iers.IERS_A_URL)
        except Exception as exception:
            self.logger.exception(exception)
            self.iers_a = iers.IERS_A.open(iers.IERS_A_URL_MIRROR)
        self.logger.info("IERS data download completed.")

    def update_kvalue_validation_result(self) -> None:
        """This method informs the k-value validation result
        to central node after DLN start/restart.

        :return: None
        :rtype: None
        """
        dish_kvalue_validation_manager = DishkValueValidationManager(
            self, self.logger
        )
        if dish_kvalue_validation_manager.is_dish_manager_ready():
            dish_kvalue_validation_manager.validate_dish_kvalue()
        elif self.kvalue_validation_callback:
            self.kValueValidationResult = ResultCode.NOT_ALLOWED
            self.kvalue_validation_callback()

    def convert_timestamp(self, timestamp_milliseconds: float) -> str:
        """Converts the floating point timestamp in milliseconds to a utc
        timestamp with format -> %Y-%m-%d %H:%M:%S

        :param timestamp_milliseconds: Input timestamp with time in
            milliseconds
        :type timestamp_milliseconds: float

        :return: Timestamp in string with format "%Y-%m-%d %H:%M:%S".
        :rtype: string
        """
        timestamp_seconds = timestamp_milliseconds / 1000
        timestamp = datetime.datetime.fromtimestamp(
            timestamp_seconds
        ).strftime("%Y-%m-%d %H:%M:%S")
        return timestamp

    def process_actual_pointing(self) -> None:
        """Process the achieved pointing data to calculate actual pointing.

        :return: None
        :rtype: None
        """
        self.logger.info("Main Process ID: %s", os.getppid())
        self.logger.info("Sub-Process ID: %s", os.getpid())
        while self.actual_pointing_process_alive.is_set() is False:
            if not self.achieved_pointing_data.empty():
                try:
                    self.perform_reverse_transform(
                        self.achieved_pointing_data.get(block=True).tolist()
                    )
                except ValueError as value_error:
                    self.logger.exception(
                        "Value error occurred in actual pointing process: %s",
                        value_error,
                    )
                except Exception as exception:
                    self.logger.exception(
                        "Error in actual pointing process: %s", exception
                    )

    def perform_reverse_transform(self, value_list):
        """
        Performs the reverse transform and publishes it on the actualPointing
        attribute.

        :param value_list: A list containing timestamp in milliseconds,azimuth,
            and elevation.
        :type value_list: (List[float])

        :return: None
        :rtype: None
        """
        try:
            timestamp_milliseconds, azimuth, elevation = value_list
            azimuth = azimuth - (
                list(self.received_pointing_data)[0].pointing_data[1]
                / math.cos(elevation)
            )
            elevation = (
                elevation
                - list(self.received_pointing_data)[0].pointing_data[2]
            )
            timestamp = self.convert_timestamp(timestamp_milliseconds)
            right_ascension, declination = self.converter.azel_to_radec(
                str(azimuth),
                str(elevation),
                timestamp,
            )
            self.actual_pointing = [timestamp, right_ascension, declination]
        except (ValueError, IndexError) as exception:
            self.logger.exception(
                "No values on achievedPointing dish master attribute,"
                "the device will continue with its normal operation.: %s",
                exception,
            )

    def stop_event_receiver(self) -> None:
        """Stops the Event Receiver

        :return: None
        """
        if self.event_receiver_object._thread.is_alive():
            self.event_receiver_object.stop()

    def get_device(self) -> DishDeviceInfo:
        """
        Return the device info of the monitoring loop with name dev_name

        :return: a device info
        :rtype: DishDeviceInfo
        """
        return self._device

    # pylint: disable=signature-differs
    def off(self, task_callback: TaskCallbackType) -> Tuple[TaskStatus, str]:
        """Submits the Off command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.off_command.invoke_off,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("Off command queued for execution")
        return task_status, response

    def setstandbyfpmode(
        self, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """
        Initializes the attributes and properties of the DishLeafNode.

        :return: A tuple containing a return code and a string message
            indicating status. The message is for information purpose
            only.
        """
        task_status, response = self.submit_task(
            self.setstandbyfpmode_command.set_standby_fp_mode,
            args=[self.logger],
            is_cmd_allowed=self.is_command_allowed_callable(
                "SetStandbyFPMode"
            ),
            task_callback=task_callback,
        )
        self.logger.info("SetStandbyFPMode command queued for execution")
        return task_status, response

    def setstandbylpmode(
        self, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """Submits the SetStandbyLPMode command for execution.

        :param task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.setstandbylpmode_command.set_standby_lp_mode,
            args=[self.logger],
            is_cmd_allowed=self.is_command_allowed_callable(
                "SetStandbyLPMode"
            ),
            task_callback=task_callback,
        )
        self.logger.info("SetStandbyLPMode command queued for execution")
        return task_status, response

    def setstowmode(
        self, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """Submits the SetStowMode command for execution.

        :param task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.setstowmode_command.set_stow_mode,
            args=[self.logger],
            is_cmd_allowed=self.is_command_allowed_callable("SetStowMode"),
            task_callback=task_callback,
        )
        self.logger.info("SetStowMode command queued for execution")
        return task_status, response

    def scan(
        self, argin: str, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """Submits the Scan command for execution.

        :param argin: JSON string containing offsets in the form of param.
        :type: str
        :param task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.scan_command.scan,
            args=[argin, self.logger],
            is_cmd_allowed=self.is_command_allowed_callable("Scan"),
            task_callback=task_callback,
        )
        self.logger.info("Scan command queued for execution")
        return task_status, response

    def endscan(
        self, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """Submits the EndScan command for execution.

        :param task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.endscan_command.endscan,
            args=[self.logger],
            is_cmd_allowed=self.is_command_allowed_callable("EndScan"),
            task_callback=task_callback,
        )
        self.logger.info("EndScan command queued for execution")
        return task_status, response

    def is_track_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.

        :return: True if the command is allowed in the current operational
            state, False otherwise.
        :rtype: boolean
        """
        if self.dishMode == DishMode.OPERATE and self.pointingState not in (
            PointingState.NONE,
            PointingState.UNKNOWN,
        ):
            return True

        raise CommandNotAllowed(
            "The invocation of the Track command on this"
            + "device is not allowed."
            + "Reason: The current dish mode is"
            + f"{self.dishMode} and poiniting state : {self.pointingState}"
            + "The command has NOT been executed."
            + "This device will continue with normal operation."
        )

    def track(
        self, argin: str, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """Submits the Track command for execution.


        :param argin: JSON string containing offsets in the form of param.
        :type: str
        :param task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        try:
            input_json = json.loads(argin)
        except json.JSONDecodeError as exception:
            self.logger.exception(
                "Exception occured while loading the input json: %s", exception
            )
            return (
                ResultCode.FAILED,
                f"Error while loading the input json: {exception}",
            )

        # validate the JSON argument
        validation_result, message = self.track_command.validate_json_argument(
            input_json
        )
        if validation_result != ResultCode.OK:
            return validation_result, message

        task_status, response = self.submit_task(
            self.track_command.track,
            args=[input_json, self.logger],
            is_cmd_allowed=self.is_track_and_trackstop_command_allowed,
            task_callback=task_callback,
        )
        self.logger.info("Track command queued for execution")
        return task_status, response

    def is_trackstop_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.

        :return: True if the command is allowed in the current operational
            state, False otherwise.
        :rtype: boolean
        """
        if self.dishMode == DishMode.OPERATE and self.pointingState not in (
            PointingState.NONE,
            PointingState.UNKNOWN,
        ):
            return True

        raise CommandNotAllowed(
            "The invocation of the TrackStop command on this"
            + "device is not allowed."
            + "Reason: The current dish mode is"
            + f"{self.dishMode} and PointingState is: {self.pointingState}"
            + "The command has NOT been executed."
            + "This device will continue with normal operation."
        )

    def trackstop(
        self, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """Submits the TrackStop command for execution.

        :param task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.trackstop_command.trackstop,
            args=[self.logger],
            is_cmd_allowed=self.is_track_and_trackstop_command_allowed,
            task_callback=task_callback,
        )
        self.logger.info("TrackStop command queued for execution")
        return task_status, response

    def setoperatemode(
        self, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """Submits the SetOperateMode command for execution.

        :param task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.setoperatemode_command.set_operate_mode,
            args=[self.logger],
            is_cmd_allowed=self.is_command_allowed_callable("SetOperateMode"),
            task_callback=task_callback,
        )
        self.logger.info("SetOperateMode command queued for execution")
        return task_status, response

    def configure(self, argin: str, task_callback: TaskCallbackType) -> tuple:
        """
        Submit the Configure command in queue.

        :return: a result code and message
        :rtype: Tuple
        """
        try:
            input_json = json.loads(argin)
        except json.JSONDecodeError as exception:
            self.logger.exception(
                "Exception occured while loading the input json: %s", exception
            )
            return (
                ResultCode.FAILED,
                f"Error while loading the input json: {exception}",
            )

        # validate the JSON argument
        (
            validation_result,
            message,
        ) = self.configure_command.validate_json_argument(input_json)
        if validation_result != ResultCode.OK:
            return validation_result, message

        # submit the command to the queue
        task_status, response = self.submit_task(
            self.configure_command.invoke_configure,
            args=[argin, self.logger],
            is_cmd_allowed=self.is_command_allowed_callable("Configure"),
            task_callback=task_callback,
        )
        self.logger.info("Configure command queued for execution")
        return task_status, response

    def track_load_static_off(
        self, argin: str, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """Submits the TrackLoadStaticOff command for execution

        :param argin: JSON string containing offsets in the form of param.
        :type: str
        :task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        try:
            offsets = json.loads(argin)
            if len(offsets) != 2:
                raise ValueError(
                    f"The input string contains {len(offsets)} values,"
                    + "but should have 2."
                )
        except Exception as exception:
            self.logger.exception(
                "Exception occured while validating the argin for "
                + "TrackLoadStaticOff command: %s",
                exception,
            )
            return (
                TaskStatus.REJECTED,
                "Input argument is incorrect for TrackLoadStaticOff command.",
            )

        task_status, response = self.submit_task(
            self.track_load_static_off_command.invoke_track_load_static_off,
            args=[argin, self.logger],
            is_cmd_allowed=self.is_command_allowed_callable(
                "TrackLoadStaticOff"
            ),
            task_callback=task_callback,
        )
        self.logger.info(
            "TrackLoadStaticOff command queued for execution with argin: %s",
            argin,
        )
        return task_status, response

    def is_trackloadstaticoff_allowed(self) -> bool:
        """Checks if the command TrackLoadStaticOff is allowed.

        :return: True if the command 'TrackLoadStaticOff' is allowed,
            False otherwise.
        :rtype: boolean
        """

        self.check_device_responsive()
        return True

    def is_configure_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.

        :return: True if the command is allowed in the current operational
            state, False otherwise.
        :rtype: boolean
        """

        self.check_device_responsive()
        if self.dishMode in [
            DishMode.STANDBY_FP,
            DishMode.STOW,
            DishMode.OPERATE,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the Off command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_off_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.

        :return: True if the command is allowed in the current operational
            state, False otherwise.
        :rtype: boolean
        """

        if self.dishMode in [
            DishMode.STANDBY_FP,
            DishMode.STOW,
            DishMode.MAINTENANCE,
            DishMode.OPERATE,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the Off command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_setstowmode_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.

        :return: True if the command is allowed in the current operational
            state, False otherwise.
        :rtype: boolean
        """

        self.check_device_responsive()
        if self.dishMode in [
            DishMode.STANDBY_FP,
            DishMode.OPERATE,
            DishMode.STANDBY_LP,
            DishMode.CONFIG,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the SetStowMode command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_setoperatemode_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.

        :return: True if the command is allowed in the current operational
            state, False otherwise.
        :rtype: boolean
        """

        self.check_device_responsive()
        if self.dishMode in [
            DishMode.STANDBY_FP,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the SetOperateMode command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_setstandbyfpmode_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.

        :rtype: boolean
        """
        self.check_device_responsive()
        if self.dishMode in [
            DishMode.STANDBY_LP,
            DishMode.OPERATE,
            DishMode.STOW,
            DishMode.MAINTENANCE,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the SetStandbyFPMode command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_setstandbylpmode_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.

        :rtype: boolean
        """

        self.check_device_responsive()
        if self.dishMode in [
            DishMode.STANDBY_FP,
            DishMode.STOW,
            DishMode.MAINTENANCE,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the SetStandbyLPMode command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_scan_allowed(
        self,
    ) -> bool | CommandNotAllowed | DeviceUnresponsive:
        """Checks if the given command is allowed in current operational
        state.

        :return: True if this command is allowed to be run in current
            dish mode, raises CommandNotAllowed in case is is not allowed and
            DeviceUnresponsive in case Device is not responsive.

        :rtype: Union[bool, CommandNotAllowed, DeviceUnresponsive]
        """
        self.check_device_responsive()
        if self.dishMode in [
            DishMode.OPERATE,
            DishMode.STANDBY_FP,
            DishMode.STOW,
            DishMode.MAINTENANCE,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the Scan command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_endscan_allowed(
        self,
    ) -> bool | CommandNotAllowed | DeviceUnresponsive:
        """Checks if the given command is allowed in current operational
        state.

        :return: True if this command is allowed to be run in current
            dish mode, raises CommandNotAllowed in case is is not allowed and
            DeviceUnresponsive in case Device is not responsive.

        :rtype: Union[bool, CommandNotAllowed, DeviceUnresponsive]
        """
        self.check_device_responsive()
        if self.dishMode in [
            DishMode.OPERATE,
            DishMode.STANDBY_FP,
            DishMode.STOW,
            DishMode.MAINTENANCE,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the EndScan command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def check_device_responsive(self) -> None:
        """Checks if dish master device is responsive."""
        if self._device is None or self._device.unresponsive:
            raise DeviceUnresponsive(f"{self.dish_dev_name} not available")

    def update_device_dish_mode(self, dish_mode: DishMode) -> None:
        """
        Update the dish mode of the given dish and call
        the relative callbacks if available.

        :param dishMode: Dish mode of the device
        :type dishMode: DishMode
        """
        with self.lock:
            dev_info = self.get_device()
            dev_info.dish_mode = dish_mode
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)
            self.logger.info(f"dishMode value updated to {dish_mode}")
            if self._update_dishmode_callback:
                self._update_dishmode_callback(dish_mode)

    def update_device_pointing_state(
        self, pointingState: PointingState
    ) -> None:
        """
        Update the pointing state of the given dish and call
        the relative callbacks if available.

        :param pointingState: Pointing state of the dish device
        :type pointingState: PointingState

        :return: None
        :rtype: None
        """
        with self.lock:
            dev_info = self.get_device()
            dev_info.pointing_state = pointingState
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)
            self.logger.info(f"PointingState value updated to {pointingState}")
            if self._update_pointingstate_callback:
                self._update_pointingstate_callback(pointingState)

    def update_device_configured_band(self, configured_band: Band) -> None:
        """
        Update the configured band of the given dish and call
        the relative callbacks if available.

        :param configured_band: Configured band of the dish device
        :type configured_band: Band
        """
        with self.lock:
            dev_info = self.get_device()
            dev_info.configured_band = configured_band
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)

    def set_dish_id(self, dish_master_fqdn: str) -> None:
        """Find out dish number from DishMasterFQDN
        property e.g. mid-dish/dish-manager/SKA001
        Here, SKA001 is the dish number.
        """
        self.dish_id = re.findall(
            "\\b(?:SKA|MKT)\\d{3}\\b", dish_master_fqdn, flags=re.IGNORECASE
        )[
            0
        ]  # station names in the layout json are in capital

    def is_abortcommands_allowed(self) -> bool:
        """
        Checks whether this command is allowed
        It checks that the device is in the right state
        to execute this command and that all the
        component needed for the operation are not unresponsive

        :return: True if this command is allowed
        :rtype: boolean
        """
        # dish manager allows abortcommands in all the dish modes
        # and pointing states
        # TO DO: DishMode/s & pointing state/s decision

        self.check_device_responsive()
        return True

    def is_set_kvalue_allowed(self) -> bool:
        """
        Checks whether this command is allowed
        It checks that the device is responsive
        before invoking command.

        :return: True if this command is allowed

        :rtype: boolean
        """
        self.check_device_responsive()
        return True

    def update_program_track_table(self, program_track_table: List) -> None:
        """
        This method writes the programTrackTable attribute on dish master
        device.

        :param program_track_table: It a list of TAI time, Az and El for
            expected number of TAI times (TrackTableEntries).
        :type program_track_table: list
        :return: None
        :rtype: None
        """
        with self.tango_operation_execution_lock:
            self.dish_adapter.programTrackTable = program_track_table
        self.logger.debug("ProgramTrackTable: %s", program_track_table)

    def track_process(
        self,
        target_data: Union[str, List[str]],
        command_obj: Configure | Track,
    ) -> None:
        """
        This method manages calculation and writing of programTrackTable
        attribute on DishMaster at the required frequency.

        :param target_data: The name or RaDec for the target
        :type target_data: Union[str, List[str]]
        :param command_obj: Command Object which is used to set
            desired_pointing.
        :type command_obj: Configure or Track.
        :return: None
        :rtype: None
        """
        self.logger.info(
            "The track process name is : %s",
            Process(target=current_process().name),
        )
        self.track_table_calculator = ProgramTrackTableCalculator(
            self, self.logger
        )
        self.dish_adapter = command_obj.dish_master_adapter
        utc_now = datetime.datetime.utcnow()

        # For future timestamp few seconds are added in current time.
        # Divided by 1000 to convert ms to sec conversion.
        time_to_add = (
            2 * self.track_table_entries * self.pointing_calculation_period
        ) / 1000

        extended_time = utc_now + datetime.timedelta(seconds=time_to_add)
        self.track_table_calculator.track_table_time_stamp = extended_time

        # This is dummy calculation because first time calculation takes
        # time due to IERS file downloads
        timestamp = self.convert_timestamp(extended_time.timestamp() * 1000)
        if isinstance(target_data, str):
            self.converter.point_to_body(target_data, timestamp)
        else:
            ra, dec = target_data
            self.converter.point(ra, dec, timestamp)

        advance_time = (
            self.track_table_entries * self.pointing_calculation_period
        ) / 1000

        while self.get_track_process_event_status() is False:
            program_track_table = (
                self.track_table_calculator.calculate_program_track_table(
                    target_data, self.converter
                )
            )
            first_entry_timestamp = (
                self.track_table_calculator.track_table_start_time
            )

            # advance_time is subtracted to provide programTrackTable few
            # seconds in advance
            scheduled_time = first_entry_timestamp - advance_time

            if scheduled_time > datetime.datetime.utcnow().timestamp():
                event_priority = 1
                self.track_table_scheduler.enterabs(
                    scheduled_time,
                    event_priority,
                    self.update_program_track_table,
                    argument=(program_track_table,),
                )
                self.track_table_scheduler.run()
            else:
                self.update_program_track_table(program_track_table)
        self.logger.info("Program Track Table Calculation stopped.")

    # pylint: disable=arguments-differ
    def update_device_ping_failure(
        self, device_info: DeviceInfo, exception: str
    ) -> None:
        """Set a device to failed and call the relative callback if available

        :param device_info: a device info
        :type device_info: DeviceInfo
        :param exception: an exception
        :type: Exception
        :rtype: None
        """
        device_info.update_unresponsive(True, exception)
        with self.lock:
            if self.update_availablity_callback is not None:
                self.update_availablity_callback(False)

    def update_ping_info(self, ping: int, device_name: str) -> None:
        """
        Update a device with the correct ping information.

        :param dev_name: name of the device
        :type dev_name: str
        :param ping: device response time
        :type ping: int
        :rtype: None
        """
        with self.lock:
            self._device.ping = ping
            self._device.update_unresponsive(False)
            if self.update_availablity_callback is not None:
                self.update_availablity_callback(True)

    def update_device_long_running_command_result(
        self, lrc_result: Tuple[str, str]
    ) -> None:
        """
        Method to update task callback based on long running command result
        event data.

        :param lrc_result: longRunningCommandResult attribute event data
        :type: (Tuple[List[str], List[str]])
        """
        self.logger.info(
            "Received a longRunningCommandResult event with data: %s",
            lrc_result,
        )
        try:
            if not lrc_result:
                return
            with self.lock:
                if lrc_result == ("", ""):
                    return

                if (
                    lrc_result[0].endswith(self.supported_commands)
                    and self.command_in_progress in self.supported_commands
                ):
                    command_result, message = json.loads(lrc_result[1])

                    command_object = self.command_object.get(
                        self.command_in_progress
                    )
                    if command_result == ResultCode.OK:
                        command_object.update_task_callback(
                            ResultCode.OK, exception="Command Completed"
                        )
                    elif command_result in [
                        ResultCode.FAILED,
                        ResultCode.NOT_ALLOWED,
                        ResultCode.REJECTED,
                    ]:
                        command_object.update_task_callback(
                            ResultCode.FAILED, exception=message
                        )
        except Exception as exception:
            self.logger.error(
                "Exception while processing longRunningCommandResult",
                exception,
            )

    @property
    def elevation_limit(self) -> bool:
        """Returns the True if dish is within its mechanical limit.

        :return: True if the dish is within its mechanical elevation limit,
            False otherwise.
        :rtype: boolean
        """
        return self.el_limit

    @elevation_limit.setter
    def elevation_limit(self, elevation_limit: bool) -> None:
        """
        Sets flag for elevation limit.

        :param elevation_limit: Flag is set to True if elevation is out of
        dish's observable boundary.
        :type elevation_limit: bool
        :return: None
        :rtype: None
        """
        if self.el_limit != elevation_limit:
            self.el_limit = elevation_limit

    def set_track_process_event(self) -> None:
        """
        Sets event for track process.

        :return: None.
        :rtype: NoneType
        """
        self._track_process_event.set()

    def get_track_process_event_status(self) -> bool:
        """
        Returns track process event status

        :return: Status of track process event.
        :rtype: bool
        """
        return self._track_process_event.is_set()

    def reset_track_process_event(self) -> None:
        """
        Resets track process event

        :return: None.
        :rtype: NoneType
        """
        self._track_process_event.clear()

    def process_sqpqc_attribute_fqdn(
        self, sdpqc_fqdn: str, dish_id: str
    ) -> None:
        """Method to subscribe to SDP queue connector attribute.
        :type attribute_name: str
        :return: None
        :rtype: None
        """
        dev_name = sdpqc_fqdn.rsplit("/", 1)[0]
        # Return if same FQDN exists
        if dev_name == self.queue_connector_device_info.dev_name:
            return
        # Unsubscribe the old FQDN if new FQDN comes
        if (
            self.queue_connector_device_info.dev_name
            and dev_name != self.queue_connector_device_info.dev_name
        ):
            self.event_receiver_object.unsubscribe_sdpqc_attribute(
                self.queue_connector_device_info
            )
        # Subscribe to the SDP queue connector attribute
        self.queue_connector_device_info.dev_name = dev_name
        attribute_name = sdpqc_fqdn.rsplit("/", 1)[-1].format(dish_id=dish_id)
        self.event_receiver_object.subscribe_sdpqc_attribute(
            self.queue_connector_device_info, attribute_name
        )

        if self.queue_connector_device_info.event_id:
            self.queue_connector_device_info.subscribed_to_attribute = True
            self.queue_connector_device_info.attribute_name = attribute_name
            self.logger.info(
                "Subscribed to %s of %s.",
                self.queue_connector_device_info.attribute_name,
                self.queue_connector_device_info.dev_name,
            )
        else:
            self.queue_connector_device_info.dev_name = ""
            self.logger.exception(
                "Failed to subscribe to %s of %s.",
                self.queue_connector_device_info.attribute_name,
                self.queue_connector_device_info.dev_name,
            )

    def process_pointing_calibration(
        self, event_data: tango.EventData
    ) -> None:
        """Method to process pointing offsets received
        from SDP queue connector device
        """
        try:
            if self.queue_connector_device_info.subscribed_to_attribute:
                if self.validate_float_list(
                    event_data.attr_value.value, number_of_values=3
                ):
                    if np.isnan(event_data.attr_value.value).any():
                        self.last_pointing_data = event_data.attr_value.value
                        self.logger.error(
                            "NaN value found in %s receeived pointing data",
                            self.last_pointing_data,
                        )
                    else:
                        self.queue_connector_device_info.pointing_data = (
                            event_data.attr_value.value
                        )
                        self.received_pointing_data[:] = [
                            self.queue_connector_device_info
                        ]
                        self.last_pointing_data = event_data.attr_value.value
                        offsets = json.dumps(
                            [
                                event_data.attr_value.value[1],
                                event_data.attr_value.value[2],
                            ]
                        )
                        self.track_load_static_off_command.do(offsets)
            self.logger.info(
                "Received SDPQC pointing calibrration: %s",
                event_data.attr_value.value,
            )
        except Exception as e:
            self.logger.exception(
                f"Error while processing {event_data.attr_value.value}"
                f"Exception Message is: {e}"
            )

    def validate_float_list(self, lst: list, number_of_values: int) -> bool:
        """Method to check the list in valid format

        :type lst: list
        :type: number_of_values: int
        :return: bool
        :rtype: bool
        """
        if len(lst) != number_of_values:
            raise ValueError(
                f"The data {lst}"
                " should contain atleast {number_of_values} numbers in list."
            )

        is_all_float = all(isinstance(element, float) for element in lst)
        if not is_all_float:
            raise ValueError(
                f"The data {lst}" " received is not in expected format."
            )
        return True

    def stop_executors_and_cleanup_memory(self) -> None:
        """Method to clean up the code, stop running threads/sub-processes

        :return: None
        :rtype: None
        """
        self.logger.info("Inside stop_executors_and_cleanup_memory")

        if self.event_receiver:
            self.stop_event_receiver()

        if self.liveliness_probe_object:
            self.stop_liveliness_probe()

        if self.actual_pointing_process.is_alive():
            self.actual_pointing_process_alive.set()
            self.actual_pointing_process.join()
        del self._actual_pointing
        del self.received_pointing_data
        while not self.achieved_pointing_data.empty():
            _ = self.achieved_pointing_data.get(block=True)
        del self.achieved_pointing_data
        self.process_manager.shutdown()
        self.logger.info("stop_executors_and_cleanup_memory successful")

    def __del__(self):
        """
        DishLN Component Manager Destructor method.
        This method is automatically called when the object is about to be
        destroyed.
        """
        with self.process_lock:
            self.stop_executors_and_cleanup_memory()
