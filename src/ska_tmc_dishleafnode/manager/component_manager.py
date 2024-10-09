"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sched
import threading
import time
from logging import Logger
from multiprocessing import Event, Lock, Manager, Process, current_process
from typing import Callable, List, Tuple

import numpy as np
import tango
from astropy.time import Time
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
from ska_tmc_common.lrcr_callback import LRCRCallback

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.commands import (
    AbortCommands,
    Configure,
    ConfigureBand,
    EndScan,
    Off,
    Scan,
    SetOperateMode,
    SetStandbyFPMode,
    SetStandbyLPMode,
    SetStowMode,
    StaticPmSetup,
    Track,
    TrackLoadStaticOff,
    TrackStop,
)
from ska_tmc_dishleafnode.constants import IERS_DATA_STORAGE_PATH, SKA_EPOCH
from ska_tmc_dishleafnode.enums import CORRECTION_KEY

from .dish_kvalue_validation_manager import DishkValueValidationManager
from .event_receiver import DishLNEventReceiver
from .program_track_table_calculator import ProgramTrackTableCalculator


# pylint: disable = too-many-public-methods
class DishLNComponentManager(TmcLeafNodeComponentManager):
    """
    A component manager for The Dish Leaf Node component.
    """

    # pylint: disable=unused-argument
    def __init__(
        self: DishLNComponentManager,
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
        is_dish_abort_commands_enabled: bool = False,
        adapter_timeout: int = 2,
        elevation: float = 0.0,
        azimuth: float = 0.0,
        elevation_max_limit: float = 0.0,
        elevation_min_limit: float = 0.0,
        track_table_advance_sec: int = 6,
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
        self.rlock = threading.RLock()
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
        self.is_configure_command = False
        self.is_configureband_completed_event = threading.Event()
        self.is_setoperatemode_completed_event = threading.Event()
        self.is_track_completed_event = threading.Event()
        self.is_trackloadstaticoff_completed_event = threading.Event()

        self.elevation = elevation
        self.azimuth = azimuth
        self.elevation_max_limit = elevation_max_limit
        self.elevation_min_limit = elevation_min_limit
        self.el_limit = False
        self.is_dish_abort_commands_enabled = is_dish_abort_commands_enabled
        self.radec_value = ""
        self.process_manager = Manager()
        self._actual_pointing = self.process_manager.list()
        self.reset_command_result_values()
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
        self.long_running_result_callback = LRCRCallback(self.logger)
        self.extended_time: int = 0
        self.__command_in_progress: str = ""
        self.event_receiver = _event_receiver

        # Event Receiver
        if _event_receiver:
            self.event_receiver_object = DishLNEventReceiver(self, logger)
            self.event_receiver_object.start()

        if _liveliness_probe != LivelinessProbeType.NONE:
            self.start_liveliness_probe(_liveliness_probe)

        self.abort_event = threading.Event()
        self.track_table_scheduler = sched.scheduler(time.time, time.sleep)
        self.track_table_entries: int = track_table_entries
        self.pointing_calculation_period: int = pointing_calculation_period
        self.track_table_advance_sec: float = track_table_advance_sec
        self.track_table_calculator = ProgramTrackTableCalculator(
            self, self.logger
        )
        self.target_data: List | str
        self.track_table_process: Process = Process(target=self.track_process)
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
        self.configure_band_command = ConfigureBand(
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
        self.dish_adapter: DishAdapter | None = (
            self.configure_command.dish_master_adapter
        )

        self.static_pm_setup_command = StaticPmSetup(
            self,
            self.op_state_model,
            __adapter_factory,
            self.logger,
        )

        self.actual_pointing_process = Process(
            target=self.process_actual_pointing,
        )
        self.process_lock = Lock()
        self.kvalue_validation_thread = threading.Timer(
            5, self.update_kvalue_validation_result
        )
        self.correction_key: str = CORRECTION_KEY.NOT_SET.value
        self.create_converter_obj_and_antenna_obj()
        self.download_iers_data()
        self.kvalue_validation_thread.start()
        self.actual_pointing_process.start()

    def reset_command_result_values(self: DishLNComponentManager):
        """Method to reset the command result dictionaries for the commands
        ConfigureBand, SetOperateMode, Track and TrackLoadStaticOff"""
        self.set_operate_mode_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }
        self.track_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }
        self.configure_band_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }
        self.track_load_static_off_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }
        self.track_stop_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }
        self.scan_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }
        self.end_scan_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }

    def clear_configure_command_events_flags(self: DishLNComponentManager):
        """Method to reset the command result dictionaries, events and flgas
        utilised in Configure command"""
        self.reset_command_result_values()
        self.is_configure_command = False
        self.is_configureband_completed_event.clear()
        self.is_setoperatemode_completed_event.clear()
        self.is_track_completed_event.clear()
        self.is_trackloadstaticoff_completed_event.clear()

    def create_converter_obj_and_antenna_obj(self: DishLNComponentManager):
        """Create AzElConverter Object and antenna object"""
        # Once SKB-398 is fixed from TelModel then this
        # exception handling can be removed.
        try:
            self.converter = AzElConverter(self)
            self.converter.create_antenna_obj()
            self.logger.debug("Antenna object created")
        except Exception as exp:
            self.logger.exception("Error while creating antenna obj %s", exp)

    def is_command_allowed_callable(
        self: DishLNComponentManager, command_name: str
    ):
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
                "ConfigureBand": [
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
                "StaticPmSetup": [
                    DishMode.STANDBY_FP,
                    DishMode.OPERATE,
                    DishMode.STANDBY_LP,
                    DishMode.CONFIG,
                    DishMode.MAINTENANCE,
                    DishMode.STARTUP,
                    DishMode.SHUTDOWN,
                    DishMode.UNKNOWN,
                ],
            }

            allowed_dish_modes = command_allowed_dish_mode.get(
                command_name, []
            )

            return self.dishMode in allowed_dish_modes

        return check_dish_mode

    def is_track_and_trackstop_command_allowed(self: DishLNComponentManager):
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
    def kValueValidationResult(
        self: DishLNComponentManager, result_code: ResultCode
    ) -> None:
        """Update the k-value validation result property."""
        if self._kValueValidationResult != result_code:
            self._kValueValidationResult = result_code

    @property
    def kValue(self: DishLNComponentManager) -> int:
        """Returns the k-value"""
        return self._kvalue

    @kValue.setter
    def kValue(self: DishLNComponentManager, k_value: int) -> None:
        """Update the k-value property."""
        if self._kvalue != k_value:
            self._kvalue = k_value

    @property
    def dishMode(self: DishLNComponentManager) -> DishMode:
        """Returns the dishMode of dish master device"""
        return self._device.dish_mode

    @property
    def pointingState(self: DishLNComponentManager) -> PointingState:
        """Returns the pointingState of dish master device"""
        return self._device.pointing_state

    @property
    def dishConfiguredBand(self: DishLNComponentManager) -> str:
        """Returns the dishConfiguredBand of dish device"""
        return str(self._device.configured_band)

    @property
    def actual_pointing(self: DishLNComponentManager) -> list:
        """Returns the actualPointing of the dish device."""
        return list(self._actual_pointing)

    @property
    def command_in_progress(self: DishLNComponentManager) -> str:
        """Method to get value of current command in progress

        return: command in progress variable data
        rtype: str
        """
        return self.__command_in_progress

    @property
    def queue_connector_device_info(
        self: DishLNComponentManager,
    ) -> SdpQueueConnectorDeviceInfo:
        """Get the queue connector device object"""
        return self._queue_connector_device_info

    @command_in_progress.setter
    def command_in_progress(
        self: DishLNComponentManager, cmd_in_progress: str
    ) -> None:
        """Method used to set command in progress value.

        :param cmd_in_progress (str): Name of current command in progress

        :return: None
        """
        self.__command_in_progress = cmd_in_progress

    @actual_pointing.setter
    def actual_pointing(self: DishLNComponentManager, value: list) -> None:
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
    def last_pointing_data(self: DishLNComponentManager):
        """Property for last pointing data"""
        return self._last_pointing_data

    @last_pointing_data.setter
    def last_pointing_data(
        self: DishLNComponentManager, last_pointing_data
    ) -> None:
        """Method to update the lastPointingData attribute"""
        self._last_pointing_data = last_pointing_data
        with self.lock:
            if self._update_last_pointing_data_callback:
                self._update_last_pointing_data_callback(last_pointing_data)

    def update_source_offset_callback(
        self: DishLNComponentManager, source_offset: list
    ) -> None:
        """Method to update the sourceOffset attribute"""
        with self.lock:
            if self._update_source_offset_callback:
                self._update_source_offset_callback(source_offset)

    def download_iers_data(self: DishLNComponentManager) -> None:
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
        self: DishLNComponentManager,
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

    def update_kvalue_validation_result(self: DishLNComponentManager) -> None:
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

    def convert_timestamp(
        self: DishLNComponentManager, timestamp_tai_ska_epoch: float
    ) -> str | None:
        """Converts the timestamp in TAI format to UTC
        timestamp with format -> %Y-%m-%d %H:%M:%S
        The value 1999-12-31T23:59:28Z is the SKA_EPOCH

        :param timestamp_tai_ska_epoch: Input timestamp with time in
            TAI format with SKA epoch
        :type timestamp_tai_ska_epoch: float

        :return: Timestamp in string with format "%Y-%m-%d %H:%M:%S".
        :rtype: string
        """
        try:
            return datetime.datetime.fromtimestamp(
                Time(
                    float(timestamp_tai_ska_epoch)
                    + Time(SKA_EPOCH, scale="utc").unix_tai,
                    format="unix_tai",
                    scale="tai",
                ).unix
            ).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            self.logger.exception(
                "Received invalid achieved pointing timestamp %s from dish."
                "Exception: %s",
                timestamp_tai_ska_epoch,
                e,
            )
            return None

    def process_actual_pointing(self: DishLNComponentManager) -> None:
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

    def perform_reverse_transform(self: DishLNComponentManager, value_list):
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
            timestamp_tai_ska_epoch, azimuth, elevation = value_list
            timestamp = self.convert_timestamp(timestamp_tai_ska_epoch)
            if timestamp:
                right_ascension, declination = self.converter.azel_to_radec(
                    str(azimuth),
                    str(elevation),
                    timestamp,
                )
                self.actual_pointing = [
                    timestamp,
                    right_ascension,
                    declination,
                ]
        except Exception as exception:
            self.logger.exception(
                "No values on achievedPointing dish master attribute,"
                "the device will continue with its normal operation.: %s",
                exception,
            )

    def stop_event_receiver(self: DishLNComponentManager) -> None:
        """Stops the Event Receiver

        :return: None
        """
        if self.event_receiver_object._thread.is_alive():
            self.event_receiver_object.stop()

    def get_device(self: DishLNComponentManager) -> DishDeviceInfo:
        """
        Return the device info of the monitoring loop with name dev_name

        :return: a device info
        :rtype: DishDeviceInfo
        """
        return self._device

    def get_dishmode(self: DishLNComponentManager) -> DishMode:
        """
        Return the dishMode of the device

        :return: dish_mode
        :rtype: DishMode
        """
        self.logger.info("Dish Mode: %s", self._device.dish_mode)
        return self._device.dish_mode

    def get_pointingstate(self: DishLNComponentManager) -> PointingState:
        """
        Return the pointingState of the device

        :return: pointing_state
        :rtype: PointingState
        """
        self.logger.info("PointingState is %s", self._device.pointing_state)
        return self._device.pointing_state

    def get_dish_configured_band(self: DishLNComponentManager) -> str:
        """
        Return the configuredBand of the device

        :return: dish band
        :rtype: str
        """
        self.logger.info("Dish Band: %s", self.dishConfiguredBand)
        return self.dishConfiguredBand

    # pylint: disable=signature-differs
    def off(
        self: DishLNComponentManager, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
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
        self: DishLNComponentManager, task_callback: TaskCallbackType
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
        self: DishLNComponentManager, task_callback: TaskCallbackType
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
        self: DishLNComponentManager, task_callback: TaskCallbackType
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
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
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
        self: DishLNComponentManager, task_callback: TaskCallbackType
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

    def is_track_allowed(self: DishLNComponentManager) -> bool:
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
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
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

    def is_trackstop_allowed(self: DishLNComponentManager) -> bool:
        """Checks if the given command is allowed in current operational
        state.

        :return: True if the command is allowed in the current operational
            state, False otherwise.
        :rtype: boolean
        """
        if self.pointingState in (PointingState.TRACK, PointingState.SLEW):
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
        self: DishLNComponentManager, task_callback: TaskCallbackType
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

    def configureband(
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
    ) -> Tuple[TaskStatus, str]:
        """Submits the ConfigureBand command for execution.

        :param argin: String containing receiver band.
        :type: str
        :param task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.configure_band_command.configure_band,
            args=[argin, self.logger],
            is_cmd_allowed=self.is_command_allowed_callable("ConfigureBand"),
            task_callback=task_callback,
        )
        self.logger.info("ConfigureBand command queued for execution")
        return task_status, response

    def setoperatemode(
        self: DishLNComponentManager, task_callback: TaskCallbackType
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

    def configure(
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
    ) -> tuple:
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
        if "correction" in input_json["pointing"]:
            self.correction_key = input_json["pointing"]["correction"]
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
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
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

    # pylint: disable=arguments-differ
    def abort_commands(self) -> Tuple[TaskStatus, str]:
        """
        Invokes Abort command on Dish manager.
        """
        abort_command = AbortCommands(
            self,
            logger=self.logger,
        )
        self.abort_event.set()
        self.logger.debug("Abort event is set.")
        result_code, message = abort_command.invoke_abort()
        return result_code, message

    def is_trackloadstaticoff_allowed(self: DishLNComponentManager) -> bool:
        """Checks if the command TrackLoadStaticOff is allowed.

        :return: True if the command 'TrackLoadStaticOff' is allowed,
            False otherwise.
        :rtype: boolean
        """

        self.check_device_responsive()
        return True

    def static_pm_setup(
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
    ) -> Tuple[TaskStatus, str]:
        """Submits the StaticPmSetup command for execution

        :param argin: String giving TelModel URI.
        :type: str
        :task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.static_pm_setup_command.invoke_static_pm_setup,
            args=[argin, self.logger],
            is_cmd_allowed=self.is_command_allowed_callable("StaticPmSetup"),
            task_callback=task_callback,
        )
        self.logger.info(
            "StaticPmSetup command queued for execution with argin: %s",
            argin,
        )
        return task_status, response

    def is_staticpmsetup_allowed(self: DishLNComponentManager) -> bool:
        """Checks if the command StaticPmSetup is allowed.

        :return: True if the command 'StaticPmSetup' is allowed,
            False otherwise.
        :rtype: boolean
        """

        self.check_device_responsive()
        return True

    def is_configure_allowed(self: DishLNComponentManager) -> bool:
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

    def is_off_allowed(self: DishLNComponentManager) -> bool:
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

    def is_setstowmode_allowed(self: DishLNComponentManager) -> bool:
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

    def is_setoperatemode_allowed(self: DishLNComponentManager) -> bool:
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

    def is_configureband_allowed(self: DishLNComponentManager) -> bool:
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
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the ConfigureBand command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_setstandbyfpmode_allowed(self: DishLNComponentManager) -> bool:
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

    def is_setstandbylpmode_allowed(self: DishLNComponentManager) -> bool:
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
        self: DishLNComponentManager,
    ) -> bool:
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
        self: DishLNComponentManager,
    ) -> bool:
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

    def check_device_responsive(self: DishLNComponentManager) -> None:
        """Checks if dish master device is responsive."""
        if self._device is None or self._device.unresponsive:
            raise DeviceUnresponsive(f"{self.dish_dev_name} not available")

    def update_device_dish_mode(
        self: DishLNComponentManager, dish_mode: DishMode
    ) -> None:
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
            self.logger.info(
                f"dishMode value updated to {DishMode(dish_mode).name}"
            )
            if self._update_dishmode_callback:
                self._update_dishmode_callback(dish_mode)

    def update_device_pointing_state(
        self: DishLNComponentManager, pointingState: PointingState
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
            self.logger.info(
                "PointingState value updated to "
                + f"{PointingState(pointingState).name}"
            )
            if self._update_pointingstate_callback:
                self._update_pointingstate_callback(pointingState)

    def update_device_configured_band(
        self: DishLNComponentManager, configured_band: Band
    ) -> None:
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

    def set_dish_id(
        self: DishLNComponentManager, dish_master_fqdn: str
    ) -> None:
        """Find out dish number from DishMasterFQDN
        property e.g. mid-dish/dish-manager/SKA001
        Here, SKA001 is the dish number.
        """
        self.dish_id = re.findall(
            "\\b(?:SKA|MKT)\\d{3}\\b", dish_master_fqdn, flags=re.IGNORECASE
        )[
            0
        ]  # station names in the layout json are in capital

    def is_abortcommands_allowed(self: DishLNComponentManager) -> bool:
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

    def is_set_kvalue_allowed(self: DishLNComponentManager) -> bool:
        """
        Checks whether this command is allowed
        It checks that the device is responsive
        before invoking command.

        :return: True if this command is allowed

        :rtype: boolean
        """
        self.check_device_responsive()
        return True

    def update_program_track_table(
        self: DishLNComponentManager, program_track_table: List
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
        with self.tango_operation_execution_lock:
            try:
                self.dish_adapter.programTrackTable = program_track_table
            except (tango.DevFailed, Exception) as exception:
                self.logger.exception(
                    "Exception while writing tracktable: %s", str(exception)
                )
        self.logger.debug("ProgramTrackTable: %s", program_track_table)

    def track_process(
        self: DishLNComponentManager,
    ) -> None:
        """
        This method manages calculation and writing of programTrackTable
        attribute on DishMaster at the required frequency.

        :return: None
        :rtype: None
        """

        self.logger.info(
            "The track process name is : %s",
            Process(target=current_process().name),
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
            actual_time = first_entry_timestamp - self.track_table_advance_sec

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
            self.track_table_scheduler.run()
        self.logger.debug("Program Track Table Calculation stopped.")

        with self.tango_operation_execution_lock:
            self.dish_adapter.programTrackTable = []
        self.logger.debug("Cleared programTrackTable attribute.")

    def create_track_process(self) -> None:
        """Creates new process for programTrackTable calculation."""
        self.logger.debug("Creating new process for tracktable calculation")
        self.track_table_process = Process(target=self.track_process)

    def set_target_data(self, target_data: list | str) -> None:
        """Sets target data to for programTrackTable generation."""
        self.target_data = target_data

    def set_dish_adapter(self, dish_adapter: DishAdapter) -> None:
        """Sets dish adapter, used to write programTrackTable on the dish."""
        self.dish_adapter = dish_adapter

    def create_process_and_start_track_table_calculation(self) -> None:
        """This method create and start process for programTrackTable
        calculation."""
        try:
            if not self.track_table_process.is_alive():
                self.create_track_process()
                self.logger.debug("Starting programTrackTable calculation")
                self.track_table_process.start()
            else:
                self.logger.debug(
                    "programTrackTable calculation is already going on."
                    + " New process will not be hosted."
                )
        except Exception as exception:
            self.logger.error(
                "Exception occurred while starting programTrackTable "
                "calculation: %s",
                str(exception),
            )

    def stop_track_table_process(self):
        """Stops track process"""
        if self.track_table_process.is_alive():
            self.logger.debug("Stopping Track table process")
            self.track_table_process.join()

    # pylint: disable=arguments-differ
    def update_exception_for_unresponsiveness(
        self: DishLNComponentManager, device_info: DeviceInfo, exception: str
    ) -> None:
        """Set a device to failed and call the relative callback if available

        :param device_info: a device info
        :type device_info: DeviceInfo
        :param exception: an exception
        :type: Exception
        :rtype: None
        """
        with self.rlock:
            device_info.update_unresponsive(True, exception)
            if self.update_availablity_callback is not None:
                self.update_availablity_callback(False)

    def update_responsiveness_info(self, device_name: str) -> None:
        """
        Update a device with the correct availability information.

        :param dev_name: name of the device
        :type dev_name: str
        """
        with self.rlock:
            self.get_device().update_unresponsive(False, "")
            if self.update_availablity_callback is not None:
                self.update_availablity_callback(True)

    def update_device_long_running_command_result(
        self: DishLNComponentManager,
        device_name: str,
        lrc_result: Tuple[str, str],
    ) -> None:
        """
        Method to update task callback based on long running command result
        event data.

        :param lrc_result: longRunningCommandResult attribute event data
        :type: (Tuple[List[str], List[str]])
        """
        self.logger.info("LRC Result is:  %s", lrc_result)
        self.update_command_result(device_name, lrc_result)

    def update_command_result(self, device_name: str, value) -> None:
        """Updates the long running command result callback"""
        self.logger.info(
            "Received longRunningCommandResult event for device: %s, "
            + "with value: %s",
            device_name,
            value,
        )
        if value == ("", "") or not value:
            return
        try:
            unique_id, result_code_message = value
            result_code, message = json.loads(result_code_message)

            if "TrackLoadStaticOff" in unique_id:
                self.track_load_static_off_result["result_code"] = result_code
                self.track_load_static_off_result["message"] = message
                self.logger.debug(
                    "TrackLoadStaticOff result: %s",
                    self.track_load_static_off_result,
                )
                self.is_trackloadstaticoff_completed_event.set()
            if "ConfigureBand" in unique_id:
                self.configure_band_result["result_code"] = result_code
                self.configure_band_result["message"] = message
                self.logger.debug(
                    "ConfigureBand result: %s",
                    self.configure_band_result,
                )
                self.is_configureband_completed_event.set()
            if "SetOperateMode" in unique_id:
                self.set_operate_mode_result["result_code"] = result_code
                self.set_operate_mode_result["message"] = message
                self.logger.debug(
                    "SetOperateMode result: %s",
                    self.set_operate_mode_result,
                )
                self.is_setoperatemode_completed_event.set()
            if "Track" in unique_id and "TrackLoadStaticOff" not in unique_id:
                self.track_result["result_code"] = result_code
                self.track_result["message"] = message
                self.logger.debug(
                    "Track result: %s",
                    self.track_result,
                )
                self.is_track_completed_event.set()
            if "TrackStop" in unique_id:
                self.track_stop_result["result_code"] = result_code
                self.track_stop_result["message"] = message
                self.logger.debug(
                    "TrackStop result: %s",
                    self.track_stop_result,
                )
            if "Scan" in unique_id:
                self.scan_result["result_code"] = result_code
                self.scan_result["message"] = message
                self.logger.debug(
                    "Scan result: %s",
                    self.scan_result,
                )
            if "EndScan" in unique_id:
                self.end_scan_result["result_code"] = result_code
                self.end_scan_result["message"] = message
                self.logger.debug(
                    "EndScan result: %s",
                    self.end_scan_result,
                )

            if result_code in [
                ResultCode.FAILED,
                ResultCode.NOT_ALLOWED,
                ResultCode.REJECTED,
            ]:
                # If the Configure command is executed, below LRCR callback
                # for the commands ConfigureBand, SetOperateMode and
                # TrackLoadStaticOff is set via is invoke_configure method.
                if self.is_configure_command:
                    if (
                        ("ConfigureBand" in unique_id)
                        or ("SetOperateMode" in unique_id)
                        or ("TrackLoadStaticOff" in unique_id)
                    ):
                        self.logger.info(
                            "LRCRCallback is: %s",
                            self.long_running_result_callback,
                        )
                else:
                    self.logger.info(
                        "Updating LRCRCallback with value: %s for %s"
                        + "for device: %s",
                        value,
                        unique_id,
                        device_name,
                    )
                    self.long_running_result_callback(
                        self.command_id,
                        ResultCode.FAILED,
                        exception_msg=message,
                    )
        except Exception as exception:
            self.logger.error(
                "Exception has occurred while processing"
                "long running command result event: %s",
                exception,
            )

    @property
    def elevation_limit(self: DishLNComponentManager) -> bool:
        """Returns the True if dish is within its mechanical limit.

        :return: True if the dish is within its mechanical elevation limit,
            False otherwise.
        :rtype: boolean
        """
        return self.el_limit

    @elevation_limit.setter
    def elevation_limit(
        self: DishLNComponentManager, elevation_limit: bool
    ) -> None:
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

    def set_track_process_event(self: DishLNComponentManager) -> None:
        """
        Sets event for track process.

        :return: None.
        :rtype: NoneType
        """
        self._track_process_event.set()

    def get_track_process_event_status(self: DishLNComponentManager) -> bool:
        """
        Returns track process event status

        :return: Status of track process event.
        :rtype: bool
        """
        return self._track_process_event.is_set()

    def reset_track_process_event(self: DishLNComponentManager) -> None:
        """
        Resets track process event

        :return: None.
        :rtype: NoneType
        """
        self._track_process_event.clear()

    def process_sqpqc_attribute_fqdn(self, sdpqc_fqdn: str) -> None:
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
        attribute_name = sdpqc_fqdn.rsplit("/", 1)[-1].format(
            dish_id=self.dish_id
        )
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
        self: DishLNComponentManager, event_data: tango.EventData
    ) -> None:
        """Method to process pointing offsets received
        from SDP queue connector device
        """
        try:
            if self.correction_key == CORRECTION_KEY.UPDATE.value:
                if self.queue_connector_device_info.subscribed_to_attribute:
                    if self.validate_float_list(
                        event_data.attr_value.value, number_of_values=3
                    ):
                        if np.isnan(event_data.attr_value.value).any():
                            self.last_pointing_data = (
                                event_data.attr_value.value
                            )
                            self.logger.error(
                                "NaN value found in %s received pointing data",
                                self.last_pointing_data,
                            )
                        else:
                            self.queue_connector_device_info.pointing_data = (
                                event_data.attr_value.value
                            )
                            self.received_pointing_data[:] = [
                                self.queue_connector_device_info
                            ]
                            self.last_pointing_data = (
                                event_data.attr_value.value
                            )
                            offsets = json.dumps(
                                [
                                    event_data.attr_value.value[1],
                                    event_data.attr_value.value[2],
                                ]
                            )
                            (
                                result_code,
                                message,
                            ) = self.track_load_static_off_command.do(offsets)
                            self.logger.debug(
                                f"result code : {result_code}"
                                + f"message : {message}"
                            )

                            self.logger.debug(
                                "Pointing offsets are Updated to %s",
                                offsets,
                            )
            elif self.correction_key in [
                CORRECTION_KEY.MAINTAIN.value,
                CORRECTION_KEY.NOT_SET.value,
            ]:
                self.logger.debug(
                    "Pointing offsets are not applied to dish as"
                    " correction key is %s",
                    CORRECTION_KEY.MAINTAIN.value
                    if self.correction_key == CORRECTION_KEY.MAINTAIN.value
                    else "Not Set",
                )
            self.logger.info(
                "Received SDP Queue Connector pointing calibration: %s",
                event_data.attr_value.value,
            )
        except Exception as e:
            self.logger.exception(
                f"Error while processing {event_data.attr_value.value}"
                f"Exception Message is: {e}"
            )

    def validate_float_list(
        self: DishLNComponentManager, lst: list, number_of_values: int
    ) -> bool:
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

    def stop_executors_and_cleanup_memory(
        self: DishLNComponentManager,
    ) -> None:
        """Method to clean up the code, stop running threads/sub-processes

        :return: None
        :rtype: None
        """
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
        if self.track_table_process.is_alive():
            self.set_track_process_event()
            self.track_table_process.join()
        self.process_manager.shutdown()
        self.logger.info("stop_executors_and_cleanup_memory successful")

    def get_dish_state(self) -> Tuple[DishMode, PointingState, ResultCode]:
        """
        Returns the current state of the dish including its mode,
        pointing state,and the result code of a specified command.

        Args:
            command_id: The identifier for the command whose result is required

        Returns:
            A tuple containing:
                - DishMode: The current operational mode of the dish.
                - PointingState: The current pointing state of the dish.
                - ResultCode: The result code of the command identified by
                    command_id.
        """
        return [
            self.dishMode,
            self.pointingState,
            self.dishConfiguredBand,
        ]

    def get_track_load_static_off_result(self: DishLNComponentManager):
        """
        Return the result of the trackLoadStaticOff command execution

        :return: track_load_static_off_result
        :rtype: dict
        """
        return self.track_load_static_off_result["result_code"]

    def get_end_scan_result(self: DishLNComponentManager):
        """
        Return the result of the EndScan command execution

        :return: ResultCode from end_scan_result
        :rtype: ResultCode
        """
        return self.end_scan_result["result_code"]

    def get_scan_result(self: DishLNComponentManager):
        """
        Return the result of the Scan command execution

        :return: ResultCode from scan_result
        :rtype: ResultCode
        """
        return self.scan_result["result_code"]

    def get_track_stop_result(self: DishLNComponentManager):
        """
        Return the result of the TrackStop command execution

        :return: ResultCode from track_stop_result
        :rtype: ResultCode
        """
        return self.track_stop_result["result_code"]

    def __del__(self: DishLNComponentManager):
        """
        DishLN Component Manager Destructor method.
        This method is automatically called when the object is about to be
        destroyed.
        """
        with self.process_lock:
            self.stop_executors_and_cleanup_memory()
