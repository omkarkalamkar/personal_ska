"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
import asyncio
import copy
import datetime
import json
import os
import sched
import threading
import time
from logging import Logger
from multiprocessing import Event, Lock, Manager, Process, current_process
from typing import Callable, List, Tuple, Union

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
    TmcLeafNodeComponentManager,
)
from ska_tmc_common.lrcr_callback import LRCRCallback

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

from .common_utils import process_long_running_command_result
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
        _liveliness_probe=LivelinessProbeType.SINGLE_DEVICE,
        _event_receiver: bool = True,
        max_workers: int = 1,
        proxy_timeout: int = 500,
        sleep_time: int = 1,
        dish_availability_check_timeout: int = 40,
        command_timeout: int = 30,
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
        :param max_workers: allows to specify number of threads
            to be used by the liveliness probe;
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
            max_workers=max_workers,
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
            dish_dev_name.split("/")[-3].upper() if dish_dev_name else None
        )
        self.observer = None
        self.dish_number = None
        self._track_process_event = Event()
        self.elevation = elevation
        self.azimuth = azimuth
        self.elevation_max_limit = elevation_max_limit
        self.elevation_min_limit = elevation_min_limit
        self.el_limit = False
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
        self.update_availablity_callback = _update_availablity_callback
        self.supported_commands: Tuple[str] = (
            "Configure_TrackLoadStaticOff",
            "TrackLoadStaticOff",
            "Track",
            "SetOperateMode",
            "ConfigureBand1",
            "ConfigureBand2",
            "ConfigureBand3",
            "ConfigureBand4",
            "ConfigureBand5a",
            "ConfigureBand5b",
        )
        self.long_running_result_callback = LRCRCallback(self.logger)
        self.extended_time: int = 0
        self.__command_in_progress: str = ""
        self.command_mapping = {}
        self.event_receiver = _event_receiver

        # Event Receiver
        if _event_receiver:
            self.event_receiver_object = DishLNEventReceiver(self, logger)
            self.event_receiver_object.start()

        if _liveliness_probe:
            self.start_liveliness_probe(_liveliness_probe)

        self.track_table_scheduler = sched.scheduler(time.time, time.sleep)
        self.dish_adapter = None
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
            target=self.process_actual_pointing
        )
        self.command_object: dict = {
            "TrackLoadStaticOff": self.track_load_static_off_command,
            "Configure_TrackLoadStaticOff": self.configure_command,
        }
        self.process_lock = Lock()
        self.converter = AzElConverter(self)
        self.converter.create_antenna_obj()
        self.kvalue_validation_iers_download_thread = threading.Timer(
            5, self.start_init_operations
        )
        self.kvalue_validation_iers_download_thread.start()
        self.actual_pointing_process.start()

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
        self.logger.debug(
            "The updated actual pointing values are: %s", self._actual_pointing
        )
        if self.pointing_callback:
            self.pointing_callback(list(self._actual_pointing))

    def start_init_operations(self) -> None:
        """This method assures proper execution of kvalue validation
        and iers data download.
        """

        try:
            asyncio.run(self.run_init_threads())
        except asyncio.CancelledError:
            self.logger.exception("Initialization stopped.")

    async def run_init_threads(self) -> None:
        """Await for the completion of beolw tasks"""
        await self.update_kvalue_validation_result()
        await self.download_iers_data()

    async def download_iers_data(self) -> None:
        """Downloads and initialises the IERS file.
        Incase of error with main link, tries downloading using Mirror link.

        :return: None
        :rtype: None
        """
        try:
            self.iers_a = iers.IERS_A.open(iers.IERS_A_URL)
            self.logger.info("IERS file download completed")
        except Exception as exception:
            self.logger.exception(exception)
            self.iers_a = iers.IERS_A.open(iers.IERS_A_URL_MIRROR)

    async def update_kvalue_validation_result(self) -> None:
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
        timestamp = datetime.datetime.utcfromtimestamp(
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
            timestamp = self.convert_timestamp(timestamp_milliseconds)
            right_ascension, declination = self.converter.azel_to_radec(
                str(azimuth),
                str(elevation),
                timestamp,
                self.converter.weather_data,
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
            "The invocation of the Configure command on this"
            + "device is not allowed."
            + "Reason: The current dish mode is"
            + f"{self.dishMode}"
            + "The command has NOT been executed."
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
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
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
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
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
        property e.g. ska001/elt/master"""
        self.dish_id = dish_master_fqdn.split("/")[
            -3
        ].upper()  # station names in the layout json are in capital

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
        self.logger.debug("ProgramTrackTable: %s", program_track_table)
        self.dish_adapter.programTrackTable = program_track_table

    def track_process(
        self, ra_value: str, dec_value: str, command_obj: Configure | Track
    ) -> None:
        """
        This method manages calculation and writing of programTrackTable
        attribute on DishMaster at the required frequency.

        :param ra_value: Right Ascension of the source in hours:minutes:sec.
        :type ra_value: str
        :param dec_value: Declination of the source in
            degree:arc_minutes:arc_sec.
        :type dec_value: str
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
        azel_converter = AzElConverter(self)
        azel_converter.create_antenna_obj()
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
        azel_converter.point(ra_value, dec_value, timestamp)

        advance_time = (
            self.track_table_entries * self.pointing_calculation_period
        ) / 1000

        while self.get_track_process_event_status() is False:
            program_track_table = (
                self.track_table_calculator.calculate_program_track_table(
                    ra_value, dec_value, azel_converter
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

    def update_device_long_running_command_status(
        self, lrc_status: Tuple[List[str], List[str]]
    ) -> None:
        """
        Method to update task callback based on long running command status
        event data.

        :param lrc_status: longRunningCommandStatus attribute event data
        :type: (Tuple[List[str], List[str]])
        """
        try:
            if not lrc_status:
                return
            with self.lock:
                if (
                    lrc_status[0].endswith(self.supported_commands)
                    and self.command_in_progress in self.supported_commands
                ):
                    command_object = self.command_object.get(
                        self.command_in_progress
                    )
                    if lrc_status[1].upper() == "COMPLETED":
                        command_object.update_task_callback(ResultCode.OK)
                    elif lrc_status[1].upper() == "FAILED":
                        command_object.update_task_callback(
                            ResultCode.FAILED, lrc_status[1]
                        )
        except Exception as exception:
            self.logger.error(
                "Exception while processing longRunningCommandStatus",
                exception,
            )

    def get_lrcr_result(self, command_id: str) -> List[str]:
        """Returns long running command result for command
        with given command ID"""

        self.logger.info(f"Check ResultCode for command_id : {command_id}")
        command_dict_ref = {}
        command_dict_ref = copy.deepcopy(self.command_mapping)

        for key, command_dict in command_dict_ref.items():
            if key == command_id:
                # Iterate through the  dictionary for each command Id
                for inner_key, value in command_dict.items():
                    if inner_key == "ResultCode":
                        self.logger.info(
                            "command mapping has required command ID"
                            " and ResultCode  as here \n"
                            " %s",
                            self.command_mapping,
                        )
                        return [value]

        return [None]

    def update_device_long_running_command_result(
        self, device_name: str, value: str
    ) -> None:
        """
        Method to update task callback based on long running command result
        event data.
        """
        process_long_running_command_result(self, device_name, value)

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

    def stop_executors_and_cleanup_memory(self) -> None:
        """Method to clean up the code, stop running threads/sub-processes

        :return: None
        :rtype: None
        """
        self.logger.info("Inside stop_executors_and_cleanup_memory")
        if self.liveliness_probe_object:
            self.stop_liveliness_probe()

        if self.event_receiver:
            self.stop_event_receiver()

        if self.actual_pointing_process.is_alive():
            self.actual_pointing_process_alive.set()
            self.actual_pointing_process.join()
        self.actual_pointing[:] = [None]
        while not self.achieved_pointing_data.empty():
            _ = self.achieved_pointing_data.get(block=True)
        self.achieved_pointing_data.put(None)
        self.process_manager.shutdown()

        self.logger.info("stop_executors_and_cleanup_memory successful")

    def get_dish_state(
        self, command_id
    ) -> Tuple[DishMode, PointingState, ResultCode]:
        """Returns aggregated subarray ObsState"""

        return [
            self.dishMode,
            self.pointingState,
            self.get_lrcr_result(command_id)[0],
        ]

    def __del__(self):
        """
        DishLN Component Manager Destructor method.
        This method is automatically called when the object is about to be
        destroyed.
        """
        with self.process_lock:
            self.stop_executors_and_cleanup_memory()
