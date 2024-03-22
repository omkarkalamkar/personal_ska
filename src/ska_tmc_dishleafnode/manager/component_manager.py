"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
import asyncio
import datetime
import json
import os
import sched
import threading

# pylint: disable=W0222, too-many-lines
import time
from logging import Logger
from multiprocessing import Event, Lock, Manager, Process
from typing import Callable, List, Optional, Tuple, Union

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
from ska_tmc_dishleafnode.constants import PROGRAM_TRACK_TABLE_SIZE, TRACK_TABLE_ENTRY_SIZE

from .dish_kvalue_validation_manager import DishkValueValidationManager
from .event_receiver import DishLNEventReceiver

# pylint: disable=abstract-method
# pylint: disable=R0902


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
        command_timeout: int = 15,
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
            for sub-devices in milliseconds used by the liveliness probe;
        :param sleep_time: allows to specify the wait between
            each iteration of the liveliness probe and EventSubscriber;
        :param timeout: Time period to wait for initialization
            of adapter.
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
        self.dish_id = dish_dev_name.split("/")[-3].upper() if dish_dev_name else None
        self.observer = None
        self.dish_number = None
        self.event_track_time = threading.Event()
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
        )
        self.__command_in_progress: str = ""

        # Event Receiver
        if _event_receiver:
            self.event_receiver_object = DishLNEventReceiver(self, logger)
            self.event_receiver_object.start()

        if _liveliness_probe:
            self.start_liveliness_probe(_liveliness_probe)

        self.update_availablity_callback = _update_availablity_callback

        self.track_table_scheduler = sched.scheduler(time.time, time.sleep)
        self.program_track_table = []
        self.dish_adapter = None
        self.track_table_entries = track_table_entries
        self.pointing_calculation_period = pointing_calculation_period

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

        self.actual_pointing_process = Process(target=self.process_actual_pointing)
        self.command_object: dict = {
            "TrackLoadStaticOff": self.track_load_static_off_command,
            "Configure_TrackLoadStaticOff": self.configure_command,
        }
        self.process_lock = Lock()
        self.converter = AzElConverter(self)
        self.kvalue_validation_iers_download_thread = threading.Timer(
            5, self.start_init_operations
        )
        self.kvalue_validation_iers_download_thread.start()
        self.actual_pointing_process.start()

    @property
    def kValueValidationResult(self) -> int:
        """Returns the k-value validation result"""
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

        Returns:
            str:  command in progress variable data
        """
        return self.__command_in_progress

    @command_in_progress.setter
    def command_in_progress(self, cmd_in_progress: str):
        """Method used to set command in progress value.

        Args:
            cmd_in_progress (str): Name of current command in progress
        """
        self.__command_in_progress = cmd_in_progress

    @actual_pointing.setter
    def actual_pointing(self, value: list) -> None:
        """Update the actualPointing of the dish device.

        :param value: The list containing timestamp, RA and Dec values.
        :value dtype: list
        """
        self._actual_pointing[:] = value
        self.logger.debug("The updated actual pointing values are: %s", self._actual_pointing)
        if self.pointing_callback:
            self.pointing_callback(list(self._actual_pointing))

    def start_init_operations(self) -> None:
        """This method assures proper execution of kvalue validation
        and iers data download.
        """
        asyncio.run(self.run_init_threads())

    async def run_init_threads(self) -> None:
        """Await for the completion of beolw tasks"""
        await self.update_kvalue_validation_result()
        await self.download_iers_data()

    async def download_iers_data(self):
        """Downloads and initialises the IERS file.
        Incase of error with main link , tries downloading using Mirror link.
        """
        try:
            self.iers_a = iers.IERS_A.open(iers.IERS_A_URL)
        except Exception as exception:
            self.logger.exception(exception)
            self.iers_a = iers.IERS_A.open(iers.IERS_A_URL_MIRROR)

    async def update_kvalue_validation_result(self) -> None:
        """This method informs the k-value validation result
        to central node after DLN start/restart.
        :returns: None
        """
        dish_kvalue_validation_manager = DishkValueValidationManager(self, self.logger)
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

        :returns: Timestamp in string with format "%Y-%m-%d %H:%M:%S".
        """
        timestamp_seconds = timestamp_milliseconds / 1000
        timestamp = datetime.datetime.utcfromtimestamp(timestamp_seconds).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return timestamp

    def process_actual_pointing(self) -> None:
        """Process the achieved pointing data to calculate actual pointing."""
        self.converter.create_antenna_obj()
        self.logger.info("Main Process ID: %s", os.getppid())
        self.logger.info("Sub-Process ID: %s", os.getpid())
        while self.actual_pointing_process_alive.is_set() is False:
            if not self.achieved_pointing_data.empty():
                try:
                    self.perform_reverse_transform(
                        self.achieved_pointing_data.get(block=True).tolist()
                    )
                except Exception as e:
                    self.logger.exception("Error in actual pointing process", e)

    def perform_reverse_transform(self, value_list):
        """DO the reverse transform and publish it on
        actualPointing attribute"""
        try:
            timestamp_milliseconds, azimuth, elevation = value_list
            timestamp = self.convert_timestamp(timestamp_milliseconds)
            right_ascension, declination = self.converter.azel_to_radec(
                str(azimuth), str(elevation), timestamp, self.converter.weather_data
            )
            self.actual_pointing = [timestamp, right_ascension, declination]
        except Exception as e:
            self.logger.exception(
                "No values on achievedPointing dish master attribute,"
                "the device will continue with its normal operation.: %s",
                e,
            )

    def stop_event_receiver(self) -> None:
        """Stops the Event Receiver"""
        if self.event_receiver_object._thread.is_alive():
            self.event_receiver_object.stop()

    def get_device(self) -> DishDeviceInfo:
        """
        Return the device info of the monitoring loop with name dev_name

        :param None:
        :return: a device info
        :rtype: DishDeviceInfo
        """
        return self._device

    def off(self, task_callback: Optional[Callable] = None) -> Tuple[TaskStatus, str]:
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

    def setstandbyfpmode(self, task_callback: Optional[Callable] = None) -> Tuple[TaskStatus, str]:
        """
        Initializes the attributes and properties of the DishLeafNode.
        :return:
        A tuple containing a return code and a string message
        indicating status. The message is for information purpose only.
        """
        task_status, response = self.submit_task(
            self.setstandbyfpmode_command.set_standby_fp_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("SetStandbyFPMode command queued for execution")
        return task_status, response

    def setstandbylpmode(self, task_callback: Optional[Callable] = None) -> Tuple[TaskStatus, str]:
        """Submits the SetStandbyLPMode command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.setstandbylpmode_command.set_standby_lp_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("SetStandbyLPMode command queued for execution")
        return task_status, response

    def setstowmode(self, task_callback: Optional[Callable] = None) -> Tuple[TaskStatus, str]:
        """Submits the SetStowMode command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.setstowmode_command.set_stow_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("SetStowMode command queued for execution")
        return task_status, response

    def scan(self, argin: str, task_callback: TaskCallbackType) -> Tuple[TaskStatus, str]:
        """Submits the Scan command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.scan_command.scan,
            args=[argin, self.logger],
            task_callback=task_callback,
        )
        self.logger.info("Scan command queued for execution")
        return task_status, response

    def endscan(self, task_callback: TaskCallbackType) -> Tuple[TaskStatus, str]:
        """Submits the EndScan command for execution.

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
        self, argin: str, task_callback: Optional[Callable] = None
    ) -> Tuple[TaskStatus, str]:
        """Submits the Track command for execution.

        :rtype: Tuple
        """
        try:
            input_json = json.loads(argin)
        except json.JSONDecodeError as e:
            self.logger.exception("Exception occured while loading the input json: %s", e)
            return (
                ResultCode.FAILED,
                f"Error while loading the input json: {e}",
            )

        # validate the JSON argument
        validation_result, message = self.track_command.validate_json_argument(input_json)
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

    def trackstop(self, task_callback: Optional[Callable] = None) -> Tuple[TaskStatus, str]:
        """Submits the TrackStop command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.trackstop_command.trackstop,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("TrackStop command queued for execution")
        return task_status, response

    def setoperatemode(self, task_callback: Optional[Callable] = None) -> Tuple[TaskStatus, str]:
        """Submits the SetOperateMode command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.setoperatemode_command.set_operate_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("SetOperateMode command queued for execution")
        return task_status, response

    def configure(self, argin: str, task_callback: Optional[Callable] = None) -> tuple:
        """
        Submit the Configure command in queue.

        :return: a result code and message
        """
        try:
            input_json = json.loads(argin)
        except Exception as e:
            self.logger.exception("Exception occured while loading the input json: %s", e)
            return (
                ResultCode.FAILED,
                f"Error while loading the input json: {e}",
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

    def track_load_static_off(self, argin: str, task_callback: Callable) -> Tuple[TaskStatus, str]:
        """Submits the TrackLoadStaticOff command for execution"""
        try:
            offsets = json.loads(argin)
            if len(offsets) != 2:
                raise ValueError(
                    f"The input string contains {len(offsets)} values, but should have 2."
                )
        except Exception as exception:
            self.logger.exception(
                "Exception occured while validating the argin for TrackLoadStaticOff command: %s",
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
        self.logger.info("TrackLoadStaticOff command queued for execution with argin: %s", argin)
        return task_status, response

    def is_trackloadstaticoff_allowed(self) -> bool:
        """Checks if the command TrackLoadStaticOff is allowed."""

        self.check_device_responsive()
        return True

    def is_configure_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.
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

    def is_scan_allowed(self) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
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

    def is_endscan_allowed(self) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
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

    def update_device_pointing_state(self, pointingState: PointingState) -> None:
        """
        Update the pointing state of the given dish and call
        the relative callbacks if available.

        :param pointingState: Pointing state of the dish device
        :type pointingState: PointingState
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

    def update_program_track_table(self) -> None:
        """Write the programTrackTable attribute on dish master device."""
        program_track_table = list(self.dish_adapter.programTrackTable)
        # If programTrackTable is full, remove older entries
        if len(program_track_table) >= PROGRAM_TRACK_TABLE_SIZE:
            num_of_values_to_remove = TRACK_TABLE_ENTRY_SIZE * self.track_table_entries
            program_track_table = program_track_table[num_of_values_to_remove:]

        program_track_table = program_track_table + self.program_track_table
        self.logger.debug("The programTrackTable is %s:", program_track_table)
        self.dish_adapter.programTrackTable = program_track_table

    def track_thread(self, ra_value: str, dec_value: str, command_obj: Configure | Track) -> None:
        """
        This method manages calculation and writing of programTrackTable attribute
        on DishMaster at the rate of 20 Hz.

        Args:
            ra_value (str): RA value in hours:minutes:sec
            dec_value (str): Dec Value in degree:arc_minutes:arc_sec
            command_obj: Command Object which is used to set desired_pointing
        """
        self.logger.info(
            "The track thread name is : %s %s",
            threading.current_thread().name,
            threading.get_ident(),
        )
        azel_converter = AzElConverter(self)
        azel_converter.create_antenna_obj()
        self.dish_adapter = command_obj.dish_master_adapter
        utc_now = datetime.datetime.utcnow()

        # For future timestamp few seconds are added in current time.
        # Divided by 1000 to convert ms to sec conversion.
        time_to_add = (2 * self.track_table_entries * self.pointing_calculation_period) / 1000
        self.extended_time = utc_now + datetime.timedelta(seconds=time_to_add)

        timestamp = self.convert_timestamp(self.extended_time.timestamp())
        azel_converter.point(ra_value, dec_value, timestamp)
        advance_time = self.track_table_entries * self.pointing_calculation_period

        while self.event_track_time.is_set() is False:
            self.program_track_table_calculator(ra_value, dec_value, azel_converter)
            first_entry_timestamp = self.program_track_table[0]
            # advance_time is subtracted to provide programTrackTable few seconds in advance
            # Divided by 1000 for milliseconds to seconds conversion
            scheduled_time = (first_entry_timestamp - advance_time) / 1000
            if scheduled_time > datetime.datetime.utcnow().timestamp():
                event_priority = 1
                self.track_table_scheduler.enterabs(
                    scheduled_time, event_priority, self.update_program_track_table
                )
                self.track_table_scheduler.run()
            else:
                with self.lock:
                    self.update_program_track_table()

    def program_track_table_calculator(
        self, ra_value: str, dec_value: str, azel_converter
    ) -> None:
        """This method calculates one set on timestamp, Az and El.

        Args:
            ra_value (str): RA value in hours:minutes:sec
            dec_value (str): Dec Value in degree:arc_minutes:arc_sec
        """
        self.program_track_table.clear()
        for _ in range(self.track_table_entries):
            utc_timestamp = self.extended_time.timestamp() * 1000
            timestamp = self.convert_timestamp(utc_timestamp)
            az_value, el_value = azel_converter.point(ra_value, dec_value, timestamp)
            if not self._is_elevation_within_mechanical_limits(el_value):
                time.sleep(self.pointing_calculation_period)
                continue
            if az_value < 0:
                az_value = 360 - abs(az_value)
            if self.event_track_time.is_set():
                log_message = (
                    "Stop the Thread as event track time is set: "
                    f"{self.event_track_time.is_set()}"
                )
                self.logger.debug(log_message)
                break

            self.program_track_table.append(utc_timestamp)
            self.program_track_table.append(round(az_value, 12))
            self.program_track_table.append(round(el_value, 12))

            self.extended_time = self.extended_time + datetime.timedelta(
                milliseconds=self.pointing_calculation_period
            )
            time.sleep(0.00005)

    def _is_elevation_within_mechanical_limits(
        self,
        el_value,
    ):
        """Check if elevation is within mechanical limit

        Args:
            el_value: string
        Return:
            bool
        """

        if not self.elevation_min_limit <= el_value <= self.elevation_max_limit:
            self.elevation_limit = True
            self.logger.info(
                "Minimum/maximum elevation limit has been reached."
                + " Source is not visible currently."
            )
            return False

        self.elevation_limit = False
        return True

    # pylint: disable=arguments-differ
    def update_device_ping_failure(self, device_info: DeviceInfo, exception: str) -> None:
        """Set a device to failed and call the relative callback if available

        :param device_info: a device info
        :type device_info: DeviceInfo
        :param exception: an exception
        :type: Exception
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
        Method to update task callback based on long running command status event data.

        Args:
            lrc_status (Tuple[List[str], List[str]]): longRunningCommandStatus
            attribute event data
        """
        try:
            if not lrc_status:
                return
            with self.lock:
                if (
                    lrc_status[0].endswith(self.supported_commands)
                    and self.command_in_progress in self.supported_commands
                ):
                    command_object = self.command_object.get(self.command_in_progress)
                    if lrc_status[1].upper() == "COMPLETED":
                        command_object.update_task_callback(ResultCode.OK)
                    elif lrc_status[1].upper() == "FAILED":
                        command_object.update_task_callback(ResultCode.FAILED, lrc_status[1])
        except Exception as exception:
            self.logger.error("Exception while processing longRunningCommandStatus", exception)

    @property
    def elevation_limit(self) -> bool:
        """Returns the True if dish is within its mechanical limit."""
        return self.el_limit

    @elevation_limit.setter
    def elevation_limit(self, elevation_limit: bool) -> None:
        """Sets flag for elevation limit."""
        if self.el_limit != elevation_limit:
            self.el_limit = elevation_limit

    def stop_executors_and_cleanup_memory(self):
        """Method to clean up the code, stop running threads/sub-processes"""
        self.logger.info("Inside stop_executors_and_cleanup_memory")
        if self.actual_pointing_process.is_alive():
            self.stop_event_receiver()
            self.stop_liveliness_probe()
            self.actual_pointing_process_alive.set()
            self.actual_pointing_process.join()
            self.actual_pointing[:] = [None]
            while not self.achieved_pointing_data.empty():
                _ = self.achieved_pointing_data.get(block=True)
            self.achieved_pointing_data.put(None)
            self.process_manager.shutdown()
            self.logger.info("stop_executors_and_cleanup_memory successful")

    def __del__(self):
        """
        DishLN Component Manager Destructor method.
        This method is automatically called when the object is about to be destroyed.
        """
        self.logger.info("Inside Component Manager Destructor")
        with self.process_lock:
            self.stop_executors_and_cleanup_memory()
