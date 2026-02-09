"""
This module provides an implementation of the Dish Leaf Node ComponentManager.

"""
from __future__ import annotations

import datetime
import json
import os
import queue
import re
import signal
import threading
import time
from collections import defaultdict
from functools import partial
from logging import Logger
from multiprocessing import Event, Lock, Manager, Process
from queue import Queue
from typing import Callable, Dict, Optional, Tuple, Union

import numpy as np
import tango
from astropy.time import Time
from astropy.utils import iers
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from ska_tango_base.executor import TaskStatus
from ska_telmodel.data import TMData
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
    TrackTableLoadMode,
)
from ska_tmc_common.adapters import DishAdapter, DishlnPointingDeviceAdapter
from ska_tmc_common.lrcr_callback import LRCRCallback
from ska_tmc_common.v2.tmc_component_manager import TmcLeafNodeComponentManager

from ska_tmc_dishleafnode.auto_stow import AutoStow
from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.commands import (
    Abort,
    ApplyPointingModel,
    Configure,
    ConfigureBand,
    EndScan,
    Off,
    Scan,
    SetStandbyFPMode,
    SetStandbyLPMode,
    SetStowMode,
    Track,
    TrackLoadStaticOff,
    TrackStop,
)
from ska_tmc_dishleafnode.constants import (
    ALLOWED_BANDS,
    IERS_DATA_STORAGE_PATH,
    SKA_EPOCH,
)
from ska_tmc_dishleafnode.enums.enums import CORRECTION_KEY, CapabilityStates
from ska_tmc_dishleafnode.enums.stow_status import StowStatus
from ska_tmc_dishleafnode.manager.gpm_validator import GPMValidator
from ska_tmc_dishleafnode.manager.health_data import (
    DishHealthStateAndInfoManager,
)

from .dish_kvalue_validation_manager import DishkValueValidationManager
from .event_manager import DishLNEventManager


# pylint: disable = too-many-public-methods,too-many-instance-attributes
class DishLNComponentManager(TmcLeafNodeComponentManager):
    """
    A component manager for The Dish Leaf Node component.

    """

    # pylint: disable=unused-argument
    def __init__(
        self: DishLNComponentManager,
        dish_dev_name: str,
        dishln_pointing_fqdn: str,
        logger: Logger,
        _update_dishmode_callback: Callable,
        _update_dish_pointing_model_param: Callable,
        _update_pointingstate_callback: Callable,
        communication_state_callback: Callable,
        component_state_callback: Callable,
        pointing_callback: Callable,
        kvalue_validation_callback: Callable,
        _update_availablity_callback: Callable,
        _update_source_offset_callback: Callable,
        _update_last_pointing_data_cb: Callable,
        _update_track_table_errors_callback: Callable,
        _update_health_state_callback: Callable,
        _update_health_info_callback: Callable,
        _update_gpm_version_callback: Callable,
        _update_gpm_validation_result_callback: Callable,
        _update_gpm_paths_data_callback: Callable,
        _liveliness_probe=LivelinessProbeType.NONE,
        _event_manager: bool = False,
        default_array_layout_source_uris: str = '',
        default_array_layout_path: str = '',
        proxy_timeout: int = 500,
        event_subscription_check_period: int = 1,
        liveliness_check_period: int = 1,
        dish_availability_check_timeout: int = 40,
        command_timeout: int = 30,
        is_dish_abort_commands_enabled: bool = False,
        adapter_timeout: int = 2,
        max_track_table_retry: int = 3,
        track_table_retry_duration: float = 0.2,
        weather_station_device_names: Optional[list] = None,
        wind_speed_threshold: float = 13.5,
        gust_speed_threshold: float = 20.0,
        operational_wind_speed_threshold: float = 10.0,
        operational_perc_mean_diff_threshold: float = 4.5,
        mean_wind_speed_duration: float = 600.0,
        mean_gust_speed_duration: float = 3.0,
        operational_wind_speed_duration: float = 1000.0,
        operational_perc_mean_diff_duration: float = 600.0,
        max_temp_threshold: float = 40.0,
        min_temp_threshold: float = -5.0,
        time_delta: float = 1000.0,
        temp_delta: float = 4.5,
        percentile_for_diff: float = 95.0,
        is_auto_stow_enabled: bool = True,
        _update_roc_temp_callback: Optional[Callable] = None,
        _update_mean_gust_speed_callback: Optional[Callable] = None,
        _update_mean_wind_speed_callback: Optional[Callable] = None,
        _update_stow_status_callback: Optional[Callable] = None,
        _update_mean_operational_speed_callback: Optional[Callable] = None,
        _update_mean_operational_diff_callback: Optional[Callable] = None,
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
        :param event_manager: flag used to control whether
            EventManager object should be instantiated or not
        :param proxy_timeout: allows to specify a client side timeout
            for sub-devices in milliseconds used by the liveliness probe
        :param event_subscription_check_period: (int) Time in seconds for
            sleep intervals in the event subscription thread.
        :param liveliness_check_period: (int) Period for the liveliness probe
            to monitor each device in a loop
        :param adapter_timeout: (int) Timeout for the adapter creation
        :param command_timeout: (int) Timeout for the command execution
        :param weather_station_device_names: (list) The Names of
            weather station devices.
        :param wind_speed_threshold: (float) Threshold on wind speed(unit m/s)
            for auto stowing.
        :param gust_speed_threshold: (float) Threshold on gust wind
            speed(unit m/s) for auto stowing.
        :param mean_wind_speed_duration: (float) Wind speed tracking
            duration(unit seconds) for auto stowing.
        :param mean_gust_speed_duration: (float) Gust wind speed tracking
            duration(unit seconds) for auto stowing.
        :param max_temp_threshold: (float) Maximum Temperature(unit °C)
            threshold for auto stowing.
        :param min_temp_threshold: (float) Minimum Temperature(unit °C)
            threshold for auto stowing.
        :param time_delta: (float) Temperature delta(unit °C) to calculate
            the rate of change in temperature for auto stowing.
        :param temp_delta: (float) Time delta(unit seconds) to calculate
            the rate of change in temperature for auto stowing.
        :param is_auto_stow_enabled: (bool) Flag to enable AutoStow feature.
        :param _update_roc_temp_callback: (Callable) Callback to update
            the rate of change in temperature attribute.
        :param _update_mean_gust_speed_callback: (Callable) Callback
            to update the mean gust speed attribute.
        :param _update_mean_wind_speed_callback: (Callable) Callback
            to update the mean wind speed attribute.
        :param _update_stow_status_callback: (Callable) Callback
            to update the stow status attribute.
        """
        super().__init__(
            logger=logger,
            _liveliness_probe=_liveliness_probe,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            proxy_timeout=proxy_timeout,
            event_subscription_check_period=event_subscription_check_period,
            liveliness_check_period=liveliness_check_period,
        )
        self.event_manager = _event_manager
        self.default_array_layout_source_uris = (
            default_array_layout_source_uris
        )
        self.weather_station_device_names: list = weather_station_device_names
        self.default_array_layout_path = default_array_layout_path
        self.rlock = threading.RLock()
        self.lock = threading.RLock()
        self.configured_band_lock = threading.RLock()
        self.dish_pointing_lock = threading.RLock()
        self.band_capability_lock = threading.RLock()
        self.dish_mode_lock = threading.RLock()
        self.pointing_state_lock = threading.RLock()
        self.health_state_lock = threading.RLock()
        self.source_offset_lock = threading.RLock()
        self._devices: list = []
        self._device = DishDeviceInfo(dish_dev_name)
        self.devices = self._device
        self.add_weather_station_devices(weather_station_device_names)

        self.logger = logger
        self.adapter_factory = AdapterFactory()
        self.health_manager = DishHealthStateAndInfoManager(self, logger)
        self.command_timeout = command_timeout
        self.adapter_timeout = adapter_timeout
        self.dish_dev_name = dish_dev_name
        self.dishln_pointing_dev_name = dishln_pointing_fqdn
        self.dish_id = (
            re.findall(
                "\\b(?:SKA|MKT)\\d{3}\\b", dish_dev_name, flags=re.IGNORECASE
            )[0]
            if dish_dev_name
            else None
        )
        self.dish_pointing_model_param: Dict[str, str] = {
            "band1pointingmodelparams": "",
            "band2pointingmodelparams": "",
            "band3pointingmodelparams": "",
            "band4pointingmodelparams": "",
            "band5apointingmodelparams": "",
            "band5bpointingmodelparams": "",
        }
        self.receiver_band = None
        self.partial_configure_lrcr = ResultCode.UNKNOWN
        self.configure_band_lrcr = ResultCode.UNKNOWN
        self.partial_configure: bool = False
        self.command_result_update_lock = threading.RLock()
        self.tango_operation_execution_lock = threading.RLock()
        self.dish_number = None
        self.is_configure_event = threading.Event()
        self.is_dish_abort_commands_enabled = is_dish_abort_commands_enabled
        self.radec_value = ""
        self.process_manager = Manager()
        self._actual_pointing = self.process_manager.list()
        self.reset_command_result_values()
        self.pointing_callback = pointing_callback
        self._update_dishmode_callback = _update_dishmode_callback
        self._update_dish_pointing_model_param = (
            _update_dish_pointing_model_param
        )
        self._update_pointingstate_callback = _update_pointingstate_callback
        self._update_track_table_errors_callback = (
            _update_track_table_errors_callback
        )
        self._update_health_state_callback = _update_health_state_callback
        self._update_health_info_callback = _update_health_info_callback
        self._kvalue: int = 0
        self.process_manager = Manager()
        self._array_layout = self.process_manager.dict()
        self.layout_updated = self.process_manager.Event()
        self._current_track_table_error = ""
        self.errors_to_be_reported = []
        self.health_info: Dict = {}
        self.band_capability_state: Dict[str, CapabilityStates] = {}
        self._kValueValidationResult = ResultCode.STARTED
        self.kvalue_validation_callback = kvalue_validation_callback
        self.dish_availability_check_timeout = dish_availability_check_timeout
        self.iers_a = None
        self.observer = None
        self.achieved_pointing_data = self.process_manager.Queue()
        self.stop_actual_pointing_process = Event()
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
        self.converter = AzElConverter(self)
        self.max_track_table_retry = max_track_table_retry
        self.track_table_retry_duration = track_table_retry_duration
        self._configure_track_lrcr = ResultCode.UNKNOWN
        self.is_configure_command: bool = False
        self.configure_command_timer_list = []
        self._gpm_version = {
            f'Band_{band}': "UNKNOWN" for band in ALLOWED_BANDS
        }
        self._gpm_validation_result = {
            f'Band_{band}': ResultCode.UNKNOWN.name for band in ALLOWED_BANDS
        }
        self._gpm_source_path: str = ""
        self._gpm_file_path: str = ""
        self.handle_gpm_version_callback = _update_gpm_version_callback
        self.dish_kvalue_validation_manager = DishkValueValidationManager(
            self, self.logger
        )
        self.handle_update_gpm_validation_result_callback = (
            _update_gpm_validation_result_callback
        )
        self.store_gpm_path_data_callback = _update_gpm_paths_data_callback
        self.supported_commands = (
            "ConfigureBand",
            "ConfigureBand1",
            "ConfigureBand2",
            "ConfigureBand3",
            "ConfigureBand4",
            "ConfigureBand5a",
            "ConfigureBand5b",
            "Track",
            "EndScan",
            "Scan",
            "TrackLoadStaticOff",
            "TrackStop",
            "Abort",
            "ApplyPointingModel",
        )
        # Event Manager
        if _event_manager:
            check_period: int = event_subscription_check_period
            self.event_manager_object: DishLNEventManager = DishLNEventManager(
                self,
                logger=logger,
                event_subscription_check_period=check_period,
            )

        if _liveliness_probe == LivelinessProbeType.MULTI_DEVICE:
            self.start_liveliness_probe(_liveliness_probe)
            for device in self.devices:
                self.liveliness_probe_object.add_device(device.dev_name)

        self.abort_event = threading.Event()
        self.dish_adapter = None
        self.dishln_pointing_device_adapter = None
        self.gpm_validator = GPMValidator(self, logger)

        self.actual_pointing_process = Process(
            target=self.process_actual_pointing, daemon=True
        )
        self.process_lock = Lock()
        self.kvalue_validation_thread = threading.Timer(
            5, self.update_kvalue_validation_result
        )
        self.correction_key: str = CORRECTION_KEY.NOT_SET.value
        self.max_track_table_retry = max_track_table_retry
        self.track_table_retry_duration = track_table_retry_duration
        self.is_tracktable_provided = threading.Event()
        self.command_unique_id_dict = {}
        self._primary_configuration: dict = {}
        self.is_trackloadstatic_off: bool = False
        self.event_processing_methods = self.get_attribute_dict()
        self.event_threads: list[threading.Thread] = []
        self._stop_thread = False
        self.__humidity: float = 0.10
        self.__pressure: float = 900.0
        self.__wind_speed: float = 10.0
        self.__temperature: float = 30.0
        self.initialization_complete = threading.Event()
        self.start_event_processing_threads()
        self.setup_event_subscription()
        self.kvalue_validation_thread.start()
        self.load_array_layout_for_dish()
        self.actual_pointing_process.start()
        self.__initialize_auto_stow__(
            wind_speed_threshold,
            gust_speed_threshold,
            operational_wind_speed_threshold,
            operational_perc_mean_diff_threshold,
            temp_delta,
            time_delta,
            max_temp_threshold,
            min_temp_threshold,
            mean_wind_speed_duration,
            mean_gust_speed_duration,
            operational_wind_speed_duration,
            operational_perc_mean_diff_duration,
            is_auto_stow_enabled,
            _update_roc_temp_callback,
            _update_mean_wind_speed_callback,
            _update_mean_gust_speed_callback,
            _update_stow_status_callback,
            percentile_for_diff,
            _update_mean_operational_speed_callback,
            _update_mean_operational_diff_callback,
        )

        self.__stow_status: StowStatus = StowStatus.DISH_NOT_IN_STOW
        # this is temporary variable
        # which can be utilised to expose failure in future.

    def __initialize_auto_stow__(
        self,
        wind_speed_threshold,
        gust_speed_threshold,
        operational_wind_speed_threshold,
        operational_perc_mean_diff_threshold,
        temp_delta,
        time_delta,
        max_temp_threshold,
        min_temp_threshold,
        mean_wind_speed_duration,
        mean_gust_speed_duration,
        operational_wind_speed_duration,
        operational_perc_mean_diff_duration,
        is_auto_stow_enabled,
        _update_roc_temp_callback,
        _update_mean_wind_speed_callback,
        _update_mean_gust_speed_callback,
        _update_stow_status_callback,
        percentile_for_diff,
        _update_mean_operational_speed_callback,
        _update_mean_operational_diff_callback,
    ):
        """Initialise all variables related to auto stow functionality."""
        self.auto_stow = AutoStow(
            self,
            self.logger,
            temp_delta=temp_delta,
            time_delta=time_delta,
            wind_speed_threshold=wind_speed_threshold,
            gust_speed_threshold=gust_speed_threshold,
            max_temp_threshold=max_temp_threshold,
            min_temp_threshold=min_temp_threshold,
            mean_gust_speed_duration=mean_gust_speed_duration,
            mean_wind_speed_duration=mean_wind_speed_duration,
            operational_wind_speed_duration=operational_wind_speed_duration,
            operational_wind_speed_threshold=(
                operational_wind_speed_threshold
            ),
            operational_perc_mean_diff_threshold=(
                operational_perc_mean_diff_threshold
            ),
            operational_perc_mean_diff_duration=(
                operational_perc_mean_diff_duration
            ),
            percentile_for_diff=percentile_for_diff,
        )
        self.temperature_tracking: dict[str, bool] = defaultdict(
            threading.Event
        )
        self.__rate_of_change_temperature: dict = {}
        self.__gust_wind_speed_mean: float = 0.0
        self.__wind_speed_mean: float = 0.0

        self.temp_timers: list[threading.Thread] = []
        self.is_auto_stow_enabled: bool = is_auto_stow_enabled
        self._update_roc_temp_callback: Optional[
            Callable
        ] = _update_roc_temp_callback
        self._update_mean_wind_speed_callback: Optional[
            Callable
        ] = _update_mean_wind_speed_callback
        self._update_mean_gust_speed_callback: Optional[
            Callable
        ] = _update_mean_gust_speed_callback
        self._update_stow_status_callback: Optional[
            Callable
        ] = _update_stow_status_callback
        self._update_mean_operational_speed_callback: Optional[
            Callable
        ] = _update_mean_operational_speed_callback
        self._update_mean_operational_diff_callback: Optional[
            Callable
        ] = _update_mean_operational_diff_callback
        self.__auto_stow_failures: list[str] = [""]
        self.__operational_wind_speed_mean: float = 0.0
        self.__operational_perc_mean_diff: float = 0.0

    def update_auto_stow_failures(self, failure: str):
        """Method updates the auto stow failures"""
        self.__auto_stow_failures.append(failure)

    def add_weather_station_devices(
        self, weather_station_devices: list
    ) -> None:
        """Method to add all the weather station device info.

        :param weather_station_devices: (list) Weather station device fqdns.
        """
        if weather_station_devices:
            for wms in weather_station_devices:
                self.devices = DeviceInfo(wms.strip(), True)

    @property
    def devices(self) -> list[Union[DishDeviceInfo, DeviceInfo]]:
        """Method provides the devices monitored by CSP subarray leaf node.

        :return: returns list of device information.
        :rtype: list
        """
        return self._devices

    @devices.setter
    def devices(self, device_info: Union[DishDeviceInfo, DeviceInfo]):
        """Method appends the device information into devices list.

        :param device_info: Device information.
        :type device_info: SubArrayDeviceInfo or DeviceInfo
        """
        self._devices.append(device_info)

    @property
    def stow_status(self) -> StowStatus:
        """Property stow status.

        :return: stow status
        :rtype: StowStatus
        """
        return self.__stow_status

    @stow_status.setter
    def stow_status(self, status: StowStatus):
        self.__stow_status = status
        if self._update_stow_status_callback:
            self._update_stow_status_callback(status)

    @property
    def rate_of_change_temperature(self) -> dict:
        """Rate of change of temperature."""
        return self.__rate_of_change_temperature

    @rate_of_change_temperature.setter
    def rate_of_change_temperature(self, roc: dict):
        """setter for change of temperature.

        :param roc: rate of change of temperature
        :type roc: float
        """
        self.__rate_of_change_temperature = roc
        if self._update_roc_temp_callback:
            self._update_roc_temp_callback(json.dumps(roc))

    @property
    def gust_wind_speed_mean(self) -> float:
        """Gust of wind."""
        return self.__gust_wind_speed_mean

    @gust_wind_speed_mean.setter
    def gust_wind_speed_mean(self, speed: float):
        """Setter for gust of wind.

        :param speed: speed
        :type speed: float
        """
        self.__gust_wind_speed_mean = speed
        if self._update_mean_gust_speed_callback:
            self._update_mean_gust_speed_callback(speed)

    @property
    def operational_wind_speed_mean(self) -> float:
        """Gust of wind."""
        return self.__operational_wind_speed_mean

    @operational_wind_speed_mean.setter
    def operational_wind_speed_mean(self, speed: float):
        """Setter for gust of wind.

        :param speed: speed
        :type speed: float
        """
        self.__operational_wind_speed_mean = speed
        if self._update_mean_operational_speed_callback:
            self._update_mean_operational_speed_callback(speed)

    @property
    def operational_perc_mean_diff(self) -> float:
        """Gust of wind."""
        return self.__operational_perc_mean_diff

    @operational_perc_mean_diff.setter
    def operational_perc_mean_diff(self, speed: float):
        """Setter for gust of wind.

        :param speed: speed
        :type speed: float
        """
        self.__operational_perc_mean_diff = speed
        if self._update_mean_operational_diff_callback:
            self._update_mean_operational_diff_callback(speed)

    @property
    def wind_speed_mean(self) -> float:
        """Mean wind speed for specific duration"""
        return self.__wind_speed_mean

    @wind_speed_mean.setter
    def wind_speed_mean(self, speed: float):
        """Setter for mean wind speed"""

        self.__wind_speed_mean = speed
        if self._update_mean_wind_speed_callback:
            self._update_mean_wind_speed_callback(speed)

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
        if self.event_manager:
            self.start_event_manager(
                self.build_device_attribute_map(), timeout=1000
            )
            self.logger.debug("Successfully subscribed the events")

    def build_device_attribute_map(self) -> Dict[str, list[str]]:
        """
        Builds a dictionary mapping device names to lists of attributes
        to be subscribed.

        Returns:
            Dict[str, List[str]]: A mapping from device names to list of
            attributes.
        """
        device_attribute_map = defaultdict(list)
        device_attribute_map[self.dish_dev_name] = [
            "band1PointingModelParams",
            "band2PointingModelParams",
            "band3PointingModelParams",
            "band4PointingModelParams",
            "band5APointingModelParams",
            "band5BPointingModelParams",
            "dishMode",
            "pointingState",
            "achievedPointing",
            "configuredBand",
            "longRunningCommandResult",
            "kValue",
            "b1CapabilityState",
            "b2CapabilityState",
            "b3CapabilityState",
            "b4CapabilityState",
            "b5aCapabilityState",
            "b5bCapabilityState",
            "healthState",
        ]

        device_attribute_map[self.dishln_pointing_dev_name] = [
            "pointingProgramTrackTable",
            "programTrackTableError",
            "healthState",
        ]
        if self.weather_station_device_names:
            for (
                weather_station_device_name
            ) in self.weather_station_device_names:
                device_attribute_map[weather_station_device_name] = [
                    "humidity",
                    "temperature",
                    "windSpeed",
                    "pressure",
                ]

        self.logger.debug(
            "Device attribute map dictionary : %s", device_attribute_map
        )
        return device_attribute_map

    def load_array_layout_for_dish(self) -> None:
        """
        Load the array layout from TelModel and store the dictionary
        corresponding to this dish (matching ``station_label`` to
        ``self.dish_id``) into ``self.array_layout``.

        Raises:
            ValueError: If loading or parsing the array layout fails.
        """
        try:
            if (
                self.default_array_layout_source_uris
                and self.default_array_layout_path
            ):
                source_uris = [self.default_array_layout_source_uris]
                array_layout_path = self.default_array_layout_path
            else:
                self.logger.warning(
                    "No default array layout source URIs or path "
                    "provided; cannot load array layout."
                )
                return

            tm_data = TMData(source_uris)
            raw_layout = tm_data[array_layout_path].get_dict()

            if isinstance(raw_layout, str):
                layout = json.loads(raw_layout)
            else:
                layout = raw_layout

            receptors = layout.get("receptors", [])
            if not receptors:
                self.logger.warning(
                    "No receptors found in layout at '%s'.",
                    array_layout_path,
                )
                return

            target_id = str(self.dish_id).lower()
            matching_receptor: dict | None = None

            for receptor in receptors:
                station_label = str(receptor.get("station_label", "")).lower()
                if station_label == target_id:
                    matching_receptor = receptor
                    break

            if matching_receptor is None:
                self.logger.warning(
                    "No matching receptor found for dish_id '%s' "
                    "in layout at '%s'.",
                    self.dish_id,
                    array_layout_path,
                )
                return

            self.array_layout = matching_receptor

            self.logger.info(
                "array_layout set for dish_id '%s' "
                "using station_label '%s'.",
                self.dish_id,
                matching_receptor.get("station_label"),
            )

        except Exception as exc:
            self.logger.exception(
                "Failed to load array layout for dish_id '%s' "
                "from default_layout_schema: %s",
                getattr(self, "dish_id", "<unknown>"),
                exc,
            )
            raise ValueError(
                "Failed to load array layout for dish_id "
            ) from exc

    @property
    def configure_track_lrcr(self) -> ResultCode:
        """Configure track lrcr

        Returns:
            ResultCode: Configure track lrcr ResultCode.
        """
        return self._configure_track_lrcr

    @configure_track_lrcr.setter
    def configure_track_lrcr(self, value):
        """Set configure track lrcr"""
        with self.command_result_update_lock:
            self._configure_track_lrcr = value

    @property
    def primary_configuration(self) -> dict:
        """Return primary configuration

        Returns:
            dict: primary configuration.
        """
        return self._primary_configuration

    @property
    def gpm_version(self):
        """
        Dictionary mapping each allowed band to its GPM band version status.

        Returns:
            dict: A mapping like
            {'Band_1': 'UNKNOWN', 'Band_2': 'UNKNOWN', ...}
            where each key corresponds to a band identifier
            from ALLOWED_BANDS
            and each value indicates the current version status
            (default: 'UNKNOWN').
        """
        return self._gpm_version

    @property
    def gpm_validation_result(self) -> dict:
        """
        Dictionary mapping each allowed band to its GPM
        band validation status.

        Returns:
            dict: A mapping like
            {'Band_1': "UNKNOWN", 'Band_2': "OK", ...}
            where each key corresponds to a band validation result.
            "UNKNOWN": Default. Indicates GPM version not set for
            that band
            "FAILED": If validation fails for given band.
            "OK": If validation is successfull.
            The values are derived from ResultCode.<Enum>.name
        """
        return self._gpm_validation_result

    @property
    def gpm_source_path(self) -> str:
        """Get the GPM repository(telmodel) source path
        Returns:
            str: Stored GPM source path
        """
        return self._gpm_source_path

    @property
    def gpm_file_path(self) -> str:
        """Get the GPM repository(telmodel) file path
        Returns:
            str: Stored GPM file path
        """
        return self._gpm_file_path

    @gpm_source_path.setter
    def gpm_source_path(self, source_path: str) -> None:
        """Set the GPM repository(telmodel) source path
        Args:
            source_path(str) : GPM source path
        """
        self._gpm_source_path = source_path

    @gpm_file_path.setter
    def gpm_file_path(self, file_path: str) -> None:
        """Set the GPM repository(telmodel) file path
        Args:
            file_path(str) : GPM file path
        """
        self._gpm_file_path = file_path

    @primary_configuration.setter
    def primary_configuration(self, config: dict):
        """Set Primary configuration"""
        self._primary_configuration = config

    def reset_command_result_values(self: DishLNComponentManager):
        """Method to reset the command result dictionaries for the commands
        ConfigureBand, Track and TrackLoadStaticOff
        """
        with self.command_result_update_lock:
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
            self.abort_result = {
                "result_code": None,
                "message": None,
                "exception": None,
                "status": None,
            }
        self.logger.info("Cleared the command result dictionaries.")

    def clear_configure_command_events_flags(self: DishLNComponentManager):
        """Method to reset the command result dictionaries, events and flags
        utilized in Configure command"""
        self.reset_command_result_values()
        self.is_configure_event.clear()
        self.is_configure_command = False

    def create_converter_obj_and_antenna_obj(self: DishLNComponentManager):
        """Create AzElConverter Object and antenna object"""
        # Once SKB-398 is fixed from TelModel then this
        # exception handling can be removed.
        try:
            self.converter.create_antenna_obj()
            self.logger.debug("Antenna object created")
        except Exception as exp:
            self.logger.exception(
                "Error while creating antenna obj , Exception: %s", str(exp)
            )

    def is_command_allowed_callable(
        self: DishLNComponentManager, command_name: str
    ) -> bool:
        """
        Args:
            command_name (str): Name for the command for which the is_allowed
                check need to be applied.

        Returns:
            bool: True if command is allowed in current device state,
            False otherwise.
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

    def is_track_and_trackstop_command_allowed(
        self: DishLNComponentManager,
    ) -> bool:
        """checks if track command is allowed

        Returns:
            bool: True if command is allowed, False otherwise.
        """
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
    def array_layout(self) -> dict:
        """Returns the array layout"""
        return dict(self._array_layout)

    @array_layout.setter
    def array_layout(self, layout: dict | str) -> None:
        """Setter method for array_layout property
        :param layout: The array layout to be set.
        :value dtype: dict or str
        """
        # accept JSON strings or dicts
        if isinstance(layout, str):
            layout = json.loads(layout)
        # only update if different
        if dict(self._array_layout) != layout:
            self._array_layout.clear()
            self._array_layout.update(layout)
            self.layout_updated.set()
            self.logger.info(
                "array_layout updated and signalled to child process."
            )

    @property
    def kValue(self: DishLNComponentManager) -> int:
        """Returns the k-value

        Returns:
            int: k-value.
        """
        return self._kvalue

    @kValue.setter
    def kValue(self: DishLNComponentManager, k_value: int) -> None:
        """Update the k-value property."""
        if self._kvalue != k_value:
            self._kvalue = k_value

    @property
    def dishMode(self: DishLNComponentManager) -> DishMode:
        """Returns the dishMode of dish master device

        Returns:
            DishMode: dishMode of dish master device.
        """
        return self._device.dish_mode

    def get_dish_mode(self: DishLNComponentManager) -> DishMode:
        """Returns the dishMode of dish master device

        Returns:
            DishMode: dishMode of dish master device.
        """
        return self.dishMode

    @property
    def pointingState(self: DishLNComponentManager) -> PointingState:
        """Returns the pointingState of dish master device

        Returns:
            PointingState: pointingState of dish master device.
        """
        return self._device.pointing_state

    @property
    def dishConfiguredBand(self: DishLNComponentManager) -> str:
        """Returns the dishConfiguredBand of dish device

        Returns:
            str: dishConfiguredBand of dish device.
        """
        return str(self._device.configured_band)

    @property
    def actual_pointing(self: DishLNComponentManager) -> list:
        """Gets the actualPointing of the dish device.

        Returns:
            list: list of the actualPointing of the dish.
        """
        return list(self._actual_pointing)

    @property
    def command_in_progress(self: DishLNComponentManager) -> str:
        """Method to get value of current command in progress

        Returns:
            str: command in progress variable data.

        """
        return self.__command_in_progress

    @property
    def queue_connector_device_info(
        self: DishLNComponentManager,
    ) -> SdpQueueConnectorDeviceInfo:
        """Get the queue connector device object

        Returns:
            SdpQueueConnectorDeviceInfo:
            queue connector device object.
        """
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
        self.logger.debug(
            "The updated actual pointing values are: %s", self._actual_pointing
        )
        if self.pointing_callback:
            self.pointing_callback(list(self._actual_pointing))

    @property
    def current_track_table_error(self: DishLNComponentManager) -> str:
        """Returns the trackTableError of the dish leaf node.

        Returns:
            str: trackTableError of the dish leaf node.
        """
        return self._current_track_table_error

    @current_track_table_error.setter
    def current_track_table_error(
        self: DishLNComponentManager, value: str
    ) -> None:
        """Update the trackTableError of the dish leaf node
        :param value: Error observed in track table calculation
        :value dtype: str
        :return: None
        :rtype: None
        """
        self._current_track_table_error = value
        self.logger.debug("Track table error set to: %s", value)
        # Ensure that the value is not empty string
        if value:
            self.logger.debug("Track table error is: %s", value)
            now = datetime.datetime.now()
            current_time = now.strftime("%Y-%m-%d %H:%M:%S")
            time_added_message = current_time + ": " + value
            self.logger.debug("Time added message: %s", time_added_message)
            self.errors_to_be_reported.extend([time_added_message])

            if self._update_track_table_errors_callback:
                self._update_track_table_errors_callback(
                    self.errors_to_be_reported
                )

    @property
    def last_pointing_data(self: DishLNComponentManager) -> np.array:
        """Property for last pointing data

        Returns:
            numpy.array: Array of lap pointing data.
        """
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
        """Method to update the sourceOffset attribute

        Returns:
            list: source_offset list to be updated.
        """
        with self.source_offset_lock:
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
                str(exception),
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
                str(exception),
            )
            self.iers_a = iers.IERS_A.open(IERS_DATA_STORAGE_PATH)

    def update_kvalue_validation_result(self: DishLNComponentManager) -> None:
        """This method informs the k-value validation result
        to central node after DLN start/restart.

        :return: None
        :rtype: None
        """
        with tango.EnsureOmniThread():
            if self.dish_kvalue_validation_manager.is_dish_manager_ready():
                self.dish_kvalue_validation_manager.validate_dish_kvalue()
            elif self.kvalue_validation_callback:
                self.kValueValidationResult = ResultCode.NOT_ALLOWED
                self.kvalue_validation_callback()
            self.initialization_complete.set()

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
                str(e),
            )
            return None

    def process_actual_pointing(self: DishLNComponentManager) -> None:
        """Process the achieved pointing data to calculate actual pointing.
        Runs in a child process. Rebuilds the observer when the parent updates
        `array_layout` (signalled via `self.layout_updated`).
        """
        self.logger.info("Main Process ID: %s", os.getppid())
        self.logger.info("Sub-Process ID: %s", os.getpid())

        # Initial setup
        try:
            self.create_converter_obj_and_antenna_obj()
        except Exception as e:
            self.logger.exception(
                "Failed to create initial antenna object: %s", e
            )

        try:
            self.download_iers_data()
        except Exception as e:
            self.logger.exception("Failed to download IERS data: %s", e)

        # Keep running while the Event is NOT set
        while not self.stop_actual_pointing_process.is_set():
            # Handle layout updates
            try:
                if (
                    hasattr(self, "layout_updated")
                    and self.layout_updated.is_set()
                ):
                    self.logger.debug(
                        "array_layout update detected; rebuilding antenna."
                    )
                    try:
                        self.create_converter_obj_and_antenna_obj()
                    finally:
                        self.layout_updated.clear()
            except Exception as e:
                self.logger.exception(
                    "Error while handling layout update: %s", e
                )

            # Read queue with timeout — never block forever
            try:
                item = self.achieved_pointing_data.get(timeout=0.5)
            except queue.Empty:
                continue  # recheck event and loop

            # Shutdown sentinel
            if item is None:
                break

            try:
                value_list = item.tolist()
                self.perform_reverse_transform(value_list)
            except ValueError as value_error:
                self.logger.error(
                    "Value error occurred in actual pointing process: %s",
                    value_error,
                )
            except Exception as exception:
                self.logger.exception(
                    "Exception occurred in actual pointing process: %s",
                    str(exception),
                )

        self.logger.info("Actual pointing process exiting cleanly.")

    def perform_reverse_transform(
        self: DishLNComponentManager, value_list
    ) -> None:
        """
        Performs the reverse transform and publishes it on the actualPointing
        attribute.

        :param value_list: A list containing timestamp in
            milliseconds,azimuth, and elevation.
        :type value_list: (List[float])

        """
        try:
            timestamp_tai_ska_epoch, azimuth, elevation = value_list
            timestamp = self.convert_timestamp(timestamp_tai_ska_epoch)
            if timestamp:
                right_ascension, declination = self.converter.azel_to_radec(
                    azimuth,
                    elevation,
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
                + "the device will continue with its normal operation. "
                + "Exception: %s",
                str(exception),
            )

    def stop_event_manager(self) -> None:
        """Stops the Event Receiver"""
        if self.event_manager:
            self.event_manager_object.cancel_subscription_thread(
                self.event_thread_id
            )
            for device in self.event_manager_object.device_subscriptions:
                if self.event_manager_object.device_subscriptions.get(
                    device
                ).get("is_subscription_completed"):
                    self.event_manager_object.unsubscribe_event_async(device)

    # pylint: disable=arguments-differ
    def get_device(
        self: DishLNComponentManager, device_name: str
    ) -> Union[DishDeviceInfo, DeviceInfo]:
        """
        Return the device info of the monitoring loop with name dev_name
        :param device_name: (str) device name
        :return: a device info
        :rtype: DishDeviceInfo or DeviceInfo
        """
        for dev_info in self.devices:
            if device_name in dev_info.dev_name:
                return dev_info
        return None

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
        with self.rlock:
            device_information = self.get_device(device_name)
            if not device_information:
                return True
            if device_name != device_information.dev_name:
                return True
            return not device_information.unresponsive

    # pylint: disable=signature-differs
    def off(
        self: DishLNComponentManager, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """Submits the Off command for execution.

        Args:
            task_callback (TaskCallbackType): TaskCallback for off.

        Returns:
            Tuple[TaskStatus, str]
        """
        off_command = Off(
            self,
            self.op_state_model,
            self.adapter_factory,
            logger=self.logger,
        )
        task_status, response = self.submit_task(
            off_command.invoke_off,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info(
            "Off command queued for execution on %s", self.dish_dev_name
        )
        return task_status, response

    def setstandbyfpmode(
        self: DishLNComponentManager, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """
        Initializes the attributes and properties of the DishLeafNode.

        Args:
            task_callback (TaskCallbackType): TaskCallback for
                setstandbyfpmode.

        Returns:
            Tuple[TaskStatus, str]: A tuple containing a return code
            and a string message indicating status.
            The message is for information purpose only.
        """
        setstandbyfpmode_command = SetStandbyFPMode(
            self,
            self.op_state_model,
            self.adapter_factory,
            logger=self.logger,
        )
        task_status, response = self.submit_task(
            setstandbyfpmode_command.set_standby_fp_mode,
            args=[self.logger],
            is_cmd_allowed=self.is_command_allowed_callable(
                "SetStandbyFPMode"
            ),
            task_callback=task_callback,
        )
        self.logger.info(
            "SetStandbyFPMode command queued for execution on %s",
            self.dish_dev_name,
        )
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
        setstandbylpmode_command = SetStandbyLPMode(
            self,
            self.op_state_model,
            self.adapter_factory,
            logger=self.logger,
        )
        task_status, response = self.submit_task(
            setstandbylpmode_command.set_standby_lp_mode,
            args=[self.logger],
            is_cmd_allowed=self.is_command_allowed_callable(
                "SetStandbyLPMode"
            ),
            task_callback=task_callback,
        )
        self.logger.info(
            "SetStandbyLPMode command queued for execution on %s",
            self.dish_dev_name,
        )
        return task_status, response

    def setstowmode(
        self: DishLNComponentManager, task_callback: TaskCallbackType
    ) -> None:
        """Submits the SetStowMode command for execution.

        :param task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        self.stow_status = StowStatus.STOW_STARTED
        self.abort_event.set()
        self.observable.notify_observers(attribute_value_change=True)
        self.abort_event.clear()

        def _invoke_stow_callback(
            status=None,
            progress=None,
            result=None,
            exception=None,
        ):
            """
            Method for invoking abort callback

            :param status: Status of the task
            :type status: TaskStatus
            :param progress: progress of the task
            :type progress: int
            :param result: JSON serializable result of the task
            :type result: Any
            :param exception : exception raised from the task
            :type exception: Exception

            :return: None

            """
            # progress completed in the base class is assumed to be 50%
            progress_completed = 50
            if progress is not None:
                task_callback(progress=progress_completed + progress / 2)

            if status == TaskStatus.FAILED:
                task_callback(
                    status=status, exception=exception, result=result
                )
            elif status == TaskStatus.COMPLETED:
                task_callback(status=status, progress=100, result=result)

        # pylint: disable=unused-argument
        def _abort_commands_callback(
            status=None,
            progress=None,
            result=None,
            exception=None,
        ):
            """
            Method for abort command callback

            :param status: Status of the task
            :type status: TaskStatus
            :param progress: progress of the task
            :type progress: int
            :param result: JSON serializable result of the task
            :type result: Any
            :param exception : exception raised from the task
            :type exception: Exception

            :return: None
            """

            if progress is not None:
                task_callback(progress=progress / 2)
            if status == TaskStatus.IN_PROGRESS:
                task_callback(status=status)
            elif status == TaskStatus.COMPLETED:
                task_callback(
                    progress=50,
                )
                setstowmode_command = SetStowMode(
                    self,
                    self.op_state_model,
                    self.adapter_factory,
                    logger=self.logger,
                )
                setstowmode_command.invoke_set_stow_mode(
                    task_callback=_invoke_stow_callback,
                    task_abort_event=self.abort_event,
                )

                self.command_in_progress = "SetStowMode"

        return self.abort_tasks(task_callback=_abort_commands_callback)

    def scan(
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
    ) -> Tuple[TaskStatus, str]:
        """Submits the Scan command for execution.

        :param argin: JSON string containing offsets in the form of param.
        :type argin: str
        :param task_callback: Callback function to handle task status.
        :type task_callback: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        scan_command = Scan(
            self,
            self.op_state_model,
            self.adapter_factory,
            logger=self.logger,
        )
        task_status, response = self.submit_task(
            scan_command.scan,
            kwargs={"argin": argin},
            is_cmd_allowed=self.is_command_allowed_callable("Scan"),
            task_callback=task_callback,
        )
        self.logger.info(
            "Scan command queued for execution on %s", self.dish_dev_name
        )
        return task_status, response

    def endscan(
        self: DishLNComponentManager, task_callback: TaskCallbackType
    ) -> Tuple[TaskStatus, str]:
        """Submits the EndScan command for execution.

        :param task_callback: Callback function to handle task status.
        :type: TaskCallbackType

        :rtype: Tuple
        """
        endscan_command = EndScan(
            self,
            self.op_state_model,
            self.adapter_factory,
            logger=self.logger,
        )
        task_status, response = self.submit_task(
            endscan_command.endscan,
            is_cmd_allowed=self.is_command_allowed_callable("EndScan"),
            task_callback=task_callback,
        )
        self.logger.info(
            "EndScan command queued for execution on %s", self.dish_dev_name
        )
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
        :type argin: str
        :param task_callback: Callback function to handle task status.
        :type task_callback: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        try:
            input_json = json.loads(argin)
        except json.JSONDecodeError as exception:
            self.logger.exception(
                "Exception occured while loading the input json: %s",
                str(exception),
            )
            return (
                ResultCode.FAILED,
                f"Error while loading the input json: {exception}",
            )

        track_command = Track(
            self,
            self.op_state_model,
            self.adapter_factory,
            logger=self.logger,
            is_configure_command=False,
        )
        # validate the JSON argument
        validation_result, message = track_command.validate_json_argument(
            input_json
        )
        if validation_result != ResultCode.OK:
            return validation_result, message

        task_status, response = self.submit_task(
            track_command.track,
            kwargs={"argin": argin},
            is_cmd_allowed=self.is_track_and_trackstop_command_allowed,
            task_callback=task_callback,
        )
        self.logger.info(
            "Track command queued for execution on %s", self.dish_dev_name
        )
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
        trackstop_command = TrackStop(
            self,
            self.op_state_model,
            self.adapter_factory,
            logger=self.logger,
        )
        task_status, response = self.submit_task(
            trackstop_command.trackstop,
            is_cmd_allowed=self.is_track_and_trackstop_command_allowed,
            task_callback=task_callback,
        )
        self.logger.info(
            "TrackStop command queued for execution on %s", self.dish_dev_name
        )
        return task_status, response

    def configureband(
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
    ) -> Tuple[TaskStatus, str]:
        """Submits the ConfigureBand command for execution.

        :param argin: String containing receiver band.
        :type argin: str
        :param task_callback: Callback function to handle task status.
        :type task_callback: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """
        configure_band_command = ConfigureBand(
            self,
            self.op_state_model,
            self.adapter_factory,
            logger=self.logger,
            is_configure_command=False,
        )
        task_status, response = self.submit_task(
            configure_band_command.configure_band,
            kwargs={"argin": argin},
            is_cmd_allowed=self.is_command_allowed_callable("ConfigureBand"),
            task_callback=task_callback,
        )
        self.logger.info(
            "ConfigureBand command queued for execution on %s",
            self.dish_dev_name,
        )
        return task_status, response

    def configure(
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
    ) -> tuple:
        """
        Submit the Configure command in queue.

        Args:
            argin (str):
                configure json in string.
            task_callback (TaskCallbackType):
                TaskCallback for Configure.

        Returns:
            tuple: a result code and message

        """
        try:
            input_json = json.loads(argin)
            is_partial_configure = input_json.get("tmc", {}).get(
                "partial_configuration"
            )
        except json.JSONDecodeError as exception:
            self.logger.exception(
                "Exception occured while loading the input json: %s", exception
            )
            return (
                ResultCode.FAILED,
                f"Error while loading the input json: {exception}",
            )

        configure_command = Configure(
            self,
            self.op_state_model,
            self.adapter_factory,
            logger=self.logger,
        )

        self.dish_adapter = configure_command.dish_master_adapter

        # validate the JSON argument for main configuration
        if not is_partial_configure:
            (
                validation_result,
                message,
            ) = configure_command.validate_json_argument(input_json)
            if validation_result != ResultCode.OK:
                return validation_result, message
        if "correction" in input_json.get("pointing", {}):
            self.correction_key = input_json["pointing"]["correction"]
        # submit the command to the queue
        task_status, response = self.submit_task(
            configure_command.invoke_configure,
            kwargs={"argin": argin},
            is_cmd_allowed=self.is_command_allowed_callable("Configure"),
            task_callback=task_callback,
        )
        self.logger.info(
            "Configure command queued for execution on %s", self.dish_dev_name
        )
        return task_status, response

    def track_load_static_off(
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
    ) -> Tuple[TaskStatus, str]:
        """Submits the TrackLoadStaticOff command for execution

        :param argin: JSON string containing offsets in the form of param.
        :type argin: str
        :task_callback: Callback function to handle task status.
        :type task_callback: TaskCallbackType

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
                str(exception),
            )
            return (
                TaskStatus.REJECTED,
                "Input argument is incorrect for TrackLoadStaticOff command.",
            )

        track_load_static_off_command = TrackLoadStaticOff(
            self,
            self.op_state_model,
            self.adapter_factory,
            self.logger,
            is_configure_command=False,
        )

        task_status, response = self.submit_task(
            track_load_static_off_command.invoke_track_load_static_off,
            kwargs={"argin": argin},
            is_cmd_allowed=self.is_command_allowed_callable(
                "TrackLoadStaticOff"
            ),
            task_callback=task_callback,
        )
        self.logger.info(
            "TrackLoadStaticOff command queued for "
            + "execution with argin: %s on %s",
            argin,
            self.dish_dev_name,
        )
        return task_status, response

    def abort(self, task_callback: TaskCallbackType) -> Tuple:
        """
        Abort the Dish.

        Args:
            task_callback (TaskCallbackType): TaskCallback for Abort.

        Returns:
            Tuple of result code and message
        """
        # base classes set and clear immediately, so we set to
        # clear ongoing observers and timers.
        self.abort_event.set()
        self.observable.notify_observers(attribute_value_change=True)
        self.abort_event.clear()

        def _invoke_abort_callback(
            status=None,
            progress=None,
            result=None,
            exception=None,
        ):
            """
            Method for invoking abort callback

            :param status: Status of the task
            :type status: TaskStatus
            :param progress: progress of the task
            :type progress: int
            :param result: JSON serializable result of the task
            :type result: Any
            :param exception : exception raised from the task
            :type exception: Exception

            :return: None

            """
            # progress completed in the base class is assumed to be 50%
            progress_completed = 50
            if progress is not None:
                task_callback(progress=progress_completed + progress / 2)

            if status == TaskStatus.FAILED:
                task_callback(
                    status=status, exception=exception, result=result
                )
            elif status == TaskStatus.COMPLETED:
                task_callback(status=status, progress=100, result=result)

        # pylint: disable=unused-argument
        def _abort_commands_callback(
            status=None,
            progress=None,
            result=None,
            exception=None,
        ):
            """
            Method for abort command callback

            :param status: Status of the task
            :type status: TaskStatus
            :param progress: progress of the task
            :type progress: int
            :param result: JSON serializable result of the task
            :type result: Any
            :param exception : exception raised from the task
            :type exception: Exception

            :return: None
            """

            if progress is not None:
                task_callback(progress=progress / 2)
            if status == TaskStatus.FAILED:
                task_callback(
                    status=status, exception="Failed to abort commands"
                )
            elif status == TaskStatus.COMPLETED:
                task_callback(
                    progress=50,
                )
                abort_command = Abort(
                    self,
                    self.op_state_model,
                    self.adapter_factory,
                    logger=self.logger,
                )
                # Send dummy task_abort_event
                abort_command.invoke_abort(
                    task_callback=_invoke_abort_callback,
                    task_abort_event=threading.Event(),
                )

        # pylint: enable=unused-argument
        self.command_in_progress = "Abort"
        return self.abort_tasks(task_callback=_abort_commands_callback)

    def is_trackloadstaticoff_allowed(self: DishLNComponentManager) -> bool:
        """Checks if the command TrackLoadStaticOff is allowed.

        :return: True if the command 'TrackLoadStaticOff' is allowed,
            False otherwise.
        :rtype: boolean
        """

        self.check_device_responsive()
        return True

    def apply_pointing_model(
        self: DishLNComponentManager,
        argin: str,
        task_callback: TaskCallbackType,
    ) -> Tuple[TaskStatus, str]:
        """Submits the ApplyPointingModel command for execution

        :param argin: String giving TelModel URI.
        :type argin: str
        :param task_callback: Callback function to handle task status.
        :type task_callback: TaskCallbackType

        :return: A tuple containing TaskStatus and a message string.
        :rtype: Tuple
        """

        apply_pointing_model_command = ApplyPointingModel(
            self,
            self.op_state_model,
            self.adapter_factory,
            self.logger,
        )
        task_status, response = self.submit_task(
            apply_pointing_model_command.invoke_apply_pointing_model,
            kwargs={"argin": argin},
            is_cmd_allowed=self.is_apply_pointing_model_allowed,
            task_callback=task_callback,
        )
        self.logger.info(
            "ApplyPointingModel command queued for "
            + "execution with argin: %s on %s",
            argin,
            self.dish_dev_name,
        )
        return task_status, response

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

    def is_apply_pointing_model_allowed(
        self: DishLNComponentManager,
    ) -> bool:
        """
        Verifies the device is responsive before allowing command execution.

        Raises:
            DeviceUnresponsive: If the device is not available
            for communication.

        Returns:
            bool: True if the device is responsive.
        """

        self.check_device_responsive()
        return True

    def check_device_responsive(self: DishLNComponentManager) -> None:
        """Checks if dish master device is responsive.

        Raises:
            DeviceUnresponsive: If dish master is unresponsive.

        """
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

        with self.dish_mode_lock:
            dev_info = self.get_device(self.dish_dev_name)
            if (
                dev_info.dish_mode == DishMode.STOW
                and dish_mode != DishMode.STOW
            ):
                self.stow_status = StowStatus.DISH_NOT_IN_STOW
                if self._update_stow_status_callback:
                    self._update_stow_status_callback(
                        StowStatus.DISH_NOT_IN_STOW
                    )
            dev_info.dish_mode = dish_mode
            dev_info.last_event_arrived = time.time()
            self.logger.info(
                f"dishMode value updated to {DishMode(dish_mode).name}"
            )
            self.observable.notify_observers(attribute_value_change=True)
            if self._update_dishmode_callback:
                self._update_dishmode_callback(dish_mode)

    def update_dish_pointing_model_param(
        self, dish_param: list, band_name: str
    ) -> None:
        """
        Update the dish pointing model parameter for the specified band and
        invoke the relevant callbacks if available.

        :param dish_param: New value for the dish pointing model parameter.
        :type dish_param: str
        :param band_name: Name of the band to update.
        :type band_name: str
        """
        # Wait for component manager to complete initialization
        self.initialization_complete.wait()
        with self.dish_pointing_lock:
            self.gpm_validator.update_dish_params_and_validate_gpm(
                dish_param, band_name
            )

    def update_band_capability_state(
        self: DishLNComponentManager,
        band_capability_state: CapabilityStates,
        band_name: str,
    ) -> None:
        """
        Update the band capability state for a specific dish band and trigger
        associated callbacks.

        This method normalizes the band name by removing the "CapabilityState"
        suffix and converting to uppercase
        (with special handling for B5a and B5b).
        It updates the internal band capability state dictionary, notifies the
        health manager, and logs the state change.

        :param band_capability_state: The new capability state of the band
        :type band_capability_state: CapabilityStates
        :param band_name: The band name string (e.g., "b1CapabilityState")
        :type band_name: str
        """
        with self.band_capability_lock:
            dev_info = self.get_device(self.dish_dev_name)
            dev_info.last_event_arrived = time.time()
            # remove "CapabilityState" → "b1" → "B1"
            normalized_band = band_name[:-15].upper()
            if normalized_band == "B5A":
                normalized_band = "B5a"
            elif normalized_band == "B5B":
                normalized_band = "B5b"

            # Always record raw capability state
            self.band_capability_state[normalized_band] = band_capability_state

            # But suppress UNKNOWN for health when not OPERATE
            if (
                band_capability_state == CapabilityStates.UNKNOWN
                and self.dishMode != DishMode.OPERATE
            ):
                self.logger.debug(
                    "%s is UNKNOWN, skipping health data update "
                    "because dishMode=%s (not OPERATE).",
                    normalized_band,
                    self.dishMode,
                )
                return

            # Forward to health aggregation
            self.band_capability_state[normalized_band] = band_capability_state
            self.health_manager.update_health_data_and_aggregate(
                (normalized_band, band_capability_state),
                "DishBandCapabilityStateData",
            )
            self.logger.debug(
                "BandCapabilityState for band %s updated to %s",
                normalized_band,
                CapabilityStates(band_capability_state).name,
            )

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
        with self.pointing_state_lock:
            dev_info = self.get_device(self.dish_dev_name)
            dev_info.pointing_state = pointingState
            dev_info.last_event_arrived = time.time()
            self.logger.debug(
                "PointingState value updated to "
                + f"{PointingState(pointingState).name}"
            )

            self._update_pointingstate_callback(pointingState)
            self.observable.notify_observers(attribute_value_change=True)

    def update_device_configured_band(
        self: DishLNComponentManager, configured_band: Band
    ) -> None:
        """
        Update the configured band of the given dish and call
        the relative callbacks if available.

        :param configured_band: Configured band of the dish device
        :type configured_band: Band
        """
        with self.configured_band_lock:
            dev_info = self.get_device(self.dish_dev_name)
            dev_info.configured_band = configured_band
            dev_info.last_event_arrived = time.time()

    def set_dish_id(
        self: DishLNComponentManager, dish_master_fqdn: str
    ) -> None:
        """Find out dish number from MidDishControl
        property e.g. mid-dish/dish-manager/SKA001
        Here, SKA001 is the dish number.

        Args:
            dish_master_fqdn (str): dish master
        """
        self.dish_id = re.findall(
            "\\b(?:SKA|MKT)\\d{3}\\b", dish_master_fqdn, flags=re.IGNORECASE
        )[
            0
        ]  # station names in the layout json are in capital

    def is_abort_allowed(self: DishLNComponentManager) -> bool:
        """
        Checks whether this command is allowed
        It checks that the device is in the right state
        to execute this command and that all the
        component needed for the operation are not unresponsive

        :return: True if this command is allowed
        :rtype: boolean
        """
        # dish manager allows abort in all the dish modes
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

    @property
    def trackTableLoadMode(self) -> TrackTableLoadMode:
        """
        Returns dish's trackTableLoadMode attribute value.

        :return: TrackTableLoadMode
        :rtype: enum
        """
        return self.dish_adapter.trackTableLoadMode

    @trackTableLoadMode.setter
    def trackTableLoadMode(self, load_mode: TrackTableLoadMode) -> None:
        """
        Update dish's trackTableLoadMode attribute value.
        :param load_mode: It a list of TAI time, Az and El for
            expected number of TAI times (TrackTableEntries).
        :type load_mode: TrackTableLoadMode
        :return: None
        :rtype: None
        """
        try:
            self.dish_adapter.trackTableLoadMode = load_mode
            self.logger.debug("Updated trackTableLoadMode to %s", load_mode)
        except (tango.DevFailed, Exception) as exception:
            self.logger.exception(
                "Exception occured while setting trackTableLoadMode on"
                " the dish: %s",
                str(exception),
            )

    def update_program_track_table(
        self: DishLNComponentManager,
        program_track_table_event_data: tango.EventData,
    ) -> None:
        """
        This method writes the programTrackTable attribute on dish master
        device.

        :param program_track_table_event_data: It a list of TAI time,
         Az and El for expected number of TAI times (TrackTableEntries).
        :type program_track_table_event_data: list
        :return: None
        :rtype: None
        """

        program_track_table = json.loads(program_track_table_event_data)
        if len(program_track_table) == 0:
            self.logger.debug("TrackTable is empty.")
            return

        self.logger.debug(
            "ProgramTrackTable will be updated, "
            "will acquire tango lock for same"
        )

        with self.tango_operation_execution_lock:
            self.logger.debug("Acquired  tango lock")
            for retry in range(0, self.max_track_table_retry):
                self.logger.debug("Retry is: %s", retry)
                try:
                    self.dish_adapter.programTrackTable = program_track_table
                    self.is_tracktable_provided.set()
                    self.logger.debug("ProgramTrackTable Updated")
                    if (
                        self.trackTableLoadMode
                        is not TrackTableLoadMode.APPEND
                    ):
                        self.trackTableLoadMode = TrackTableLoadMode.APPEND

                    break

                except BaseException as exception:
                    message = "Exception while writing tracktable: %s" + str(
                        exception
                    )
                    self.logger.exception(message)
                    # Write exception into attribute once all the retries are
                    # for one write operation are completed
                    if retry == (self.max_track_table_retry - 1):
                        self.current_track_table_error = message

                retry += 1
                time.sleep(self.track_table_retry_duration)

    def clear_track_table_errors(self: DishLNComponentManager):
        """
        This method clears the variables that include track table errors
        """
        self.current_track_table_error = ""
        self.errors_to_be_reported = []

    def set_dish_adapter(self, dish_adapter: DishAdapter) -> None:
        """Sets dish adapter, used to write programTrackTable on the dish.

        Args:
            dish_adapter (DishAdapter): dish Adapter to be set,
                used to write programTrackTable on the dish.
        """
        self.logger.info("Setting dish adapter in component manager")
        self.dish_adapter = dish_adapter

    def set_dishln_pointing_device_adapter(
        self, dishln_pointing_device_adapter: DishlnPointingDeviceAdapter
    ) -> None:
        """Sets dishln pointing device adapter,
        used to write programTrackTable on the dish.

        Args:
            dishln_pointing_device_adapter (DishlnPointingDeviceAdapter):
                dishln pointing device adapter,
                used to write programTrackTable on the dish.
        """
        self.dishln_pointing_device_adapter = dishln_pointing_device_adapter

    # pylint: disable=arguments-differ
    def update_exception_for_unresponsiveness(
        self: DishLNComponentManager, device_info: DeviceInfo, exception: str
    ) -> None:
        """Set a device to failed and call the relative callback if available

        :param device_info: a device info
        :type device_info: DeviceInfo
        :param exception: an exception
        :type exception: Exception

        """
        with self.rlock:
            device_info.update_unresponsive(True, exception)
            if self.update_availablity_callback is not None:
                if self.dish_dev_name == device_info.dev_name:
                    self.update_availablity_callback(False)
                else:
                    if self.is_auto_stow_enabled:
                        for wms in self.weather_station_device_names:
                            if device_info.dev_name in wms:
                                self.logger.info(
                                    "Invoking auto stow due to connection"
                                    "failure with weather station."
                                    "Exception: %s",
                                    exception,
                                )
                                self.auto_stow.invoke_auto_stow()

    def update_responsiveness_info(self, device_name: str) -> None:
        """
        Update a device with the correct availability information.

        :param dev_name: name of the device
        :type dev_name: str
        """
        with self.rlock:
            self.get_device(device_name).update_unresponsive(False, "")
            if self.update_availablity_callback is not None:
                self.update_availablity_callback(True)

    def update_command_result(self, value) -> None:
        """
        Method to update task callback based on long running command result
        event data.

        :param value: longRunningCommandResult attribute event data
        :type value: (Tuple[List[str], List[str]])
        """

        device_name = self.get_device(self.dish_dev_name)
        self.logger.info(
            "Received longRunningCommandResult event for device: %s, "
            + "with value: %s",
            device_name,
            value,
        )
        if value == ("", "") or not value:
            return

        unique_id, result_code_message = value
        self.logger.debug(
            "Current command unique dictionary: %s",
            self.command_unique_id_dict,
        )
        if (unique_id not in self.command_unique_id_dict.values()) or (
            not unique_id.endswith(self.supported_commands)
        ):
            self.logger.info(
                "LRCR event for id %s will be ignored %s",
                unique_id,
                self.command_unique_id_dict,
            )
            return

        try:
            command_name = unique_id.split('_')[-1]
            result_code, message = json.loads(result_code_message)

            with self.command_result_update_lock:
                is_notify_observer = False
                self.logger.debug("Checking unique_id- %s", unique_id)
                if self.command_unique_id_dict[command_name] == unique_id:
                    if "ConfigureBand" in unique_id:
                        self.configure_band_result["result_code"] = result_code
                        self.configure_band_result["message"] = message
                        self.logger.debug(
                            "ConfigureBand result: %s",
                            self.configure_band_result,
                        )
                        is_notify_observer = True
                    elif "EndScan" in unique_id:
                        self.end_scan_result["result_code"] = result_code
                        self.end_scan_result["message"] = message
                        self.logger.debug(
                            "EndScan result: %s",
                            self.end_scan_result,
                        )
                        is_notify_observer = True

                    elif "Scan" in unique_id:
                        self.scan_result["result_code"] = result_code
                        self.scan_result["message"] = message
                        self.logger.debug(
                            "Scan result: %s",
                            self.scan_result,
                        )
                        is_notify_observer = True

                    elif "TrackLoadStaticOff" in unique_id:
                        self.track_load_static_off_result[
                            "result_code"
                        ] = result_code
                        self.track_load_static_off_result["message"] = message
                        self.logger.debug(
                            "TrackLoadStaticOff result: %s",
                            self.track_load_static_off_result,
                        )
                        is_notify_observer = True
                    elif "TrackStop" in unique_id:
                        self.track_stop_result["result_code"] = result_code
                        self.track_stop_result["message"] = message
                        self.logger.debug(
                            "TrackStop result: %s",
                            self.track_stop_result,
                        )
                        is_notify_observer = True
                    elif "Track" in unique_id:
                        self.track_result["result_code"] = result_code
                        self.track_result["message"] = message
                        self.logger.debug(
                            "Track result: %s",
                            self.track_result,
                        )
                        is_notify_observer = True
                    elif "Abort" in unique_id:
                        self.abort_result["result_code"] = result_code
                        self.abort_result["message"] = message
                        self.logger.debug(
                            "Abort result: %s",
                            self.abort_result,
                        )
                        is_notify_observer = True

            if is_notify_observer:
                self.observable.notify_observers(attribute_value_change=True)

            if result_code in [
                ResultCode.FAILED,
                ResultCode.NOT_ALLOWED,
                ResultCode.REJECTED,
            ]:
                # If the Configure command is executed, below LRCR callback
                # for the commands ConfigureBand and
                # TrackLoadStaticOff is set via is invoke_configure method.
                self.logger.debug(
                    "Observer %s",
                    [
                        observer.command_callback_tracker.command_id
                        for observer in self.observable.observers
                    ],
                )
                if self.command_in_progress == "Configure":
                    if ("ConfigureBand" in unique_id) or (
                        "TrackLoadStaticOff" in unique_id
                    ):
                        self.logger.debug(
                            "LRCR Callback is: %s",
                            self.long_running_result_callback,
                        )
                        self.long_running_result_callback(
                            self.command_id,
                            ResultCode.FAILED,
                            exception_msg=message,
                        )
                else:
                    self.logger.info(
                        "Updating LRCR Callback with value: %s for %s"
                        + " for device: %s ",
                        value,
                        unique_id,
                        device_name,
                    )
                    self.long_running_result_callback(
                        self.command_id,
                        ResultCode.FAILED,
                        exception_msg=message,
                    )
                self.observable.notify_observers(command_exception=True)
        except Exception as exception:
            self.logger.exception(
                "Exception has occurred while processing"
                "long running command result event: %s",
                str(exception),
            )
            self.observable.notify_observers(command_exception=True)

    def process_sqpqc_attribute_fqdn(self, sdpqc_fqdn: str) -> None:
        """Method to subscribe to SDP queue connector attribute.

        Args:
            sdpqc_fqdn (str): SDP queue connector attribute
                to be subscribed.

        """
        dev_name = sdpqc_fqdn.rsplit("/", 1)[0]
        # Return if same FQDN exists
        queue_connector_dev_name = self.queue_connector_device_info.dev_name
        if dev_name == queue_connector_dev_name:
            return
        # Unsubscribe the old FQDN if new FQDN comes
        if queue_connector_dev_name and dev_name != queue_connector_dev_name:
            if (
                self.event_manager
                and self.event_manager_object.device_subscriptions.get(
                    queue_connector_dev_name
                )
            ):
                self.event_manager_object.unsubscribe_events(
                    queue_connector_dev_name
                )

        # Subscribe to the SDP queue connector attribute
        self.queue_connector_device_info.dev_name = dev_name
        queue_connector_dev_name = self.queue_connector_device_info.dev_name
        attribute_name = sdpqc_fqdn.rsplit("/", 1)[-1].format(
            dish_id=self.dish_id
        )

        if self.event_manager:
            setattr(
                self.event_manager_object,
                f"{attribute_name.lower()}_event_callback",
                self.process_pointing_calibration,
            )
            self.event_manager_object.subscribe_events(
                subscription_configuration={
                    queue_connector_dev_name: [attribute_name]
                }
            )
            dev = self.event_manager_object.device_subscriptions.get(
                queue_connector_dev_name
            )
            if dev and dev.get("is_subscription_completed"):
                self.queue_connector_device_info.subscribed_to_attribute = True
                self.queue_connector_device_info.attribute_name = (
                    attribute_name
                )
                self.logger.debug(
                    "Subscribed to %s of %s.",
                    self.queue_connector_device_info.attribute_name,
                    queue_connector_dev_name,
                )
            else:
                queue_connector_dev_name = ""
                self.logger.exception(
                    "Failed to subscribe to %s of %s.",
                    self.queue_connector_device_info.attribute_name,
                    queue_connector_dev_name,
                )

    def process_pointing_calibration(
        self: DishLNComponentManager, event_data: tango.EventData
    ) -> None:
        """Method to process pointing offsets received
        from SDP queue connector device

        Args:
            event_data (tango.EventData): Event data of pointing calibration.
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

                            track_load_static_off_command = TrackLoadStaticOff(
                                self,
                                self.op_state_model,
                                self.adapter_factory,
                                self.logger,
                                is_configure_command=False,
                            )
                            (
                                result_code,
                                message,
                            ) = track_load_static_off_command.do(offsets)
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

        Args:
            lst (list): list to be validated.
            number_of_values (int): number of values in the list.

        Returns:
            bool: True if length of list is equal to number_of_values
            and all values are float, Else raises ValueError.

        Raises:
            ValueError: When value are not in expected format
                or list is incomplete.

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
        """Method to clean up the code, stop running threads/sub-processes"""
        if self.event_manager:
            self.stop_event_manager()
            self._stop_thread = True

        if self.liveliness_probe_object:
            self.stop_liveliness_probe()

        self.stop_event_processing_threads()
        if self.is_auto_stow_enabled:
            del self.auto_stow  # calls destructor of class AutoStow
        self.logger.debug("Stopped event processing threads successfully")

        if (
            self.actual_pointing_process
            and self.actual_pointing_process.is_alive()
        ):
            self.stop_actual_pointing_process.set()

            self.logger.debug("Waiting for actual pointing process to join")
            self.actual_pointing_process.join(timeout=5)

            # Try graceful terminate if still alive
            if self.actual_pointing_process.is_alive():
                self.logger.debug("Child still alive -> terminate()")
                self.actual_pointing_process.terminate()
                self.actual_pointing_process.join(timeout=3)

            # Force kill if STILL alive
            if self.actual_pointing_process.is_alive():
                self.logger.debug("Child still alive -> SIGKILL")
                os.kill(self.actual_pointing_process.pid, signal.SIGKILL)

            self.logger.debug("Actual pointing process exited")

        del self._actual_pointing
        del self.received_pointing_data
        del self.achieved_pointing_data
        self.process_manager.shutdown()
        self.logger.debug("stop_executors_and_cleanup_memory successful")

    def get_dish_state(
        self,
    ) -> Tuple[DishMode, PointingState, Band, ResultCode, ResultCode]:
        """
        Returns the current state of the dish including its mode,
        pointing state, band and the result code of the specified commands.

        Returns:
            Tuple: A tuple containing-
                - DishMode: The current operational mode of the dish.
                - PointingState: The current pointing state of the dish.
                - Band: The dish configured band
                - ResultCode: ConfigureBand command result code
                - ResultCode: Track command result code
        """
        return [
            self.dishMode,
            self.pointingState,
            self.dishConfiguredBand,
            self.get_configure_band_result_code(),
            self.get_track_result_code(),
        ]

    def get_track_load_static_off_result_code(self: DishLNComponentManager):
        """
        Return the result of the trackLoadStaticOff command execution

        :return: track_load_static_off_result
        :rtype: dict
        """
        with self.command_result_update_lock:
            return self.track_load_static_off_result["result_code"]

    def get_track_load_static_off_result_dict(self: DishLNComponentManager):
        """
        Return the dictionary containing TrackLoadStaticOff command execution
        status

        :return: track_load_static_off_result dictionary
        :rtype: dict
        """
        with self.command_result_update_lock:
            return self.track_load_static_off_result

    def set_track_load_static_off_result_dict(
        self: DishLNComponentManager,
        result_code=None,
        message=None,
        exception=None,
        status=None,
    ):
        """
        Set the dictionary containing TrackLoadStaticOff command execution
        status

        Args:
            result_code (ResultCode): ResultCode to be set in
                track_load_static_off_result.
            message (str): message to be set in track_load_static_off_result.
            exception (str): exception to be set in
                track_load_static_off_result.
            status (str): status to be set in track_load_static_off_result.
        """
        with self.command_result_update_lock:
            self.track_load_static_off_result["result_code"] = result_code
            self.track_load_static_off_result["message"] = message
            self.track_load_static_off_result["exception"] = exception
            self.track_load_static_off_result["status"] = status

    def get_configure_band_result_code(self: DishLNComponentManager):
        """
        Return the result code of the ConfigureBand command execution

        :return: ResultCode from dictionary configure_band_result
        :rtype: ResultCode
        """

        with self.command_result_update_lock:
            return self.configure_band_result["result_code"]

    def get_configure_band_result(self: DishLNComponentManager):
        """
        Return the result of the ConfigureBand command completion.

        :return: Returns whether the ConfigureBand command completion criteria
            is satisfied.
        :rtype: bool

        """
        with self.command_result_update_lock:
            result = (
                self.configure_band_result["result_code"] == ResultCode.OK
                and self.dishMode == DishMode.OPERATE
            )
            return result

    def get_configure_band_result_dict(self: DishLNComponentManager):
        """
        Return the dictionary containing ConfigureBand command execution status

        :return: configure_band_result dictionary
        :rtype: dict
        """
        with self.command_result_update_lock:
            return self.configure_band_result

    def set_configure_band_result_dict(
        self: DishLNComponentManager,
        result_code=None,
        message=None,
        exception=None,
        status=None,
    ):
        """
        Set the dictionary containing ConfigureBand command execution status

        Args:
            result_code (ResultCode): ResultCode to be set in
                configure_band_result.
            message (str): message to be set in configure_band_result.
            exception (str): exception to be set in configure_band_result.
            status (str): status to be set in configure_band_result.
        """
        with self.command_result_update_lock:
            self.configure_band_result["result_code"] = result_code
            self.configure_band_result["message"] = message
            self.configure_band_result["exception"] = exception
            self.configure_band_result["status"] = status

    def get_abort_result_code(self: DishLNComponentManager) -> ResultCode:
        """
        Return the result of the Abort command execution

        :return: ResultCode from the set_abort_result
        :rtype: ResultCode
        """
        with self.command_result_update_lock:
            return self.abort_result["result_code"]

    def is_abort_completed(self: DishLNComponentManager) -> bool:
        """
        Waits for expected state with or without
        transitional state. On expected state occurrence,
        it sets ResultCode to OK and stops the tracker thread.

        :return: boolean value indicating if the state change occurred or not
        """
        return (
            self.dishMode == DishMode.STANDBY_FP
            and self.abort_result["result_code"] == ResultCode.OK
        )

    def get_abort_result_dict(self: DishLNComponentManager) -> dict:
        """
        Return the dictinary containing Abort command execution status

        :return: abort_result dictionary
        :rtype: dict
        """
        with self.command_result_update_lock:
            return self.abort_result

    def get_track_result_code(self: DishLNComponentManager):
        """
        Return the result of the Track command execution

        :return: ResultCode from the track_result
        :rtype: ResultCode
        """

        with self.command_result_update_lock:
            return self.track_result["result_code"]

    def get_track_result_dict(self: DishLNComponentManager):
        """
        Return the dictionary containing Track command execution status

        :return: track_result dictionary
        :rtype: dict
        """
        with self.command_result_update_lock:
            return self.track_result

    def set_track_result_dict(
        self: DishLNComponentManager,
        result_code=None,
        message=None,
        exception=None,
        status=None,
    ):
        """
        Set the dictionary containing Track command execution status

        Args:
            result_code (ResultCode): ResultCode to be set in track_result.
            message (str): message to be set in track_result.
            exception (str): exception to be set in track_result.
            status (str): status to be set in track_result.

        """
        with self.command_result_update_lock:
            self.track_result["result_code"] = result_code
            self.track_result["message"] = message
            self.track_result["exception"] = exception
            self.track_result["status"] = status

    def get_end_scan_result_code(self: DishLNComponentManager):
        """
        Return the result of the EndScan command execution

        :return: ResultCode from end_scan_result
        :rtype: ResultCode
        """
        with self.command_result_update_lock:
            return self.end_scan_result["result_code"]

    def get_scan_result_code(self: DishLNComponentManager):
        """
        Return the result of the Scan command execution

        :return: ResultCode from scan_result
        :rtype: ResultCode
        """
        with self.command_result_update_lock:
            return self.scan_result["result_code"]

    def get_track_stop_result_code(self: DishLNComponentManager):
        """
        Return the result of the TrackStop command execution

        :return: ResultCode from track_stop_result
        :rtype: ResultCode
        """
        with self.command_result_update_lock:
            return self.track_stop_result["result_code"]

    def __del__(self: DishLNComponentManager):
        """
        DishLN Component Manager Destructor method.
        This method is automatically called when the object is about to be
        destroyed.
        """
        with self.process_lock:
            self.stop_executors_and_cleanup_memory()

    def is_configure_completed(self) -> bool:
        """
        Waits for expected state with or without
        transitional state. On expected state occurrence,
        it sets ResultCode to OK and stops the tracker thread.

        :return: boolean value indicating if the state change occurred or not
        """
        return (
            self.dishMode == DishMode.OPERATE
            and self.pointingState in (PointingState.TRACK, PointingState.SLEW)
            and self.configure_band_lrcr == ResultCode.OK
            and self.configure_track_lrcr == ResultCode.OK
            and (
                self.partial_configure_lrcr == ResultCode.OK
                if self.is_trackloadstatic_off
                else True
            )
        )

    def update_windspeed(self, wind_speed: float, wms: str = "") -> None:
        """The method to update windspeed

        :param wind_speed: the wind speed event from wms.
        :type wind_speed: float
        :param wms: the fqdn of wms
        :type wms: str
        """
        if wind_speed:
            if wms in self.weather_station_device_names[0]:
                self.wind_speed = wind_speed
            if self.is_auto_stow_enabled:
                self.auto_stow.update_wind_speed(wms, wind_speed)
                self.auto_stow.start_wind_tracking()

    def update_temperature(self, temperature: float, wms: str = "") -> None:
        """The method to update temperature

        :param temperature: The temperature event from wms.
        :type temperature: float
        """
        if temperature:
            if wms in self.weather_station_device_names[0]:
                self.temperature = temperature
            self.auto_stow.temperatures[wms] = temperature
            if self.is_auto_stow_enabled:
                if (
                    temperature > self.auto_stow.max_temp_threshold
                    or temperature < self.auto_stow.min_temp_threshold
                ):
                    self.auto_stow.invoke_auto_stow()
                if not self.temperature_tracking[wms].is_set():
                    self.temperature_tracking[wms].set()
                    self.auto_stow.start_temp_tracking(wms)

    def update_pressure(self, pressure: float, wms: str = "") -> None:
        """The method to update pressure.

        :param pressure: The pressure event from the wms.
        :type pressure: float
        """
        if pressure:
            if wms in self.weather_station_device_names[0]:
                self.pressure = pressure

    def update_humidity(self, humidity: float, wms: str = "") -> None:
        """The method to update humidity.

        :param humidity: The humidity event from the wms.
        :type humidity: float
        """
        if humidity:
            if wms in self.weather_station_device_names[0]:
                self.humidity = humidity

    def get_attribute_dict(self) -> dict:
        """
        This method will return dictionary of attributes which will
        be subscribed by TMC Dish Leaf Node.
        It will contain mapping of attribute with function which will
        process event data in TMC

        :return: Dictionary of attributes to be handled by the EventReceiver.
        """
        band1_callback = partial(
            self.update_dish_pointing_model_param,
            band_name="band1PointingModelParams",
        )
        band2_callback = partial(
            self.update_dish_pointing_model_param,
            band_name="band2PointingModelParams",
        )
        band3_callback = partial(
            self.update_dish_pointing_model_param,
            band_name="band3PointingModelParams",
        )
        band4_callback = partial(
            self.update_dish_pointing_model_param,
            band_name="band4PointingModelParams",
        )
        band5a_callback = partial(
            self.update_dish_pointing_model_param,
            band_name="band5aPointingModelParams",
        )
        band5b_callback = partial(
            self.update_dish_pointing_model_param,
            band_name="band5bPointingModelParams",
        )

        kvalue_handler = (
            self.dish_kvalue_validation_manager.validate_dish_kvalue_from_event
        )

        attributes = {
            "longRunningCommandResult": self.update_command_result,
            "dishMode": self.update_device_dish_mode,
            "pointingState": self.update_device_pointing_state,
            "kValue": kvalue_handler,
            "configuredBand": self.update_device_configured_band,
            "pointingProgramTrackTable": self.update_program_track_table,
            "programTrackTableError": self.update_program_track_table_error,
            "healthState": self.update_device_health_state,
            "band1pointingmodelparams": band1_callback,
            "band2pointingmodelparams": band2_callback,
            "band3pointingmodelparams": band3_callback,
            "band4pointingmodelparams": band4_callback,
            "band5apointingmodelparams": band5a_callback,
            "band5bpointingmodelparams": band5b_callback,
        }
        if self.weather_station_device_names:
            for wms in self.weather_station_device_names:
                if "tango://" in wms:
                    wms = "/".join(wms.split("/")[-3:])
                attributes.update(
                    {
                        f"windSpeed{wms}": partial(
                            self.update_windspeed, wms=wms
                        ),
                        f"pressure{wms}": partial(
                            self.update_pressure, wms=wms
                        ),
                        f"humidity{wms}": partial(
                            self.update_humidity, wms=wms
                        ),
                        f"temperature{wms}": partial(
                            self.update_temperature, wms=wms
                        ),
                    }
                )
        band_capabilities = [
            "b1capabilitystate",
            "b2capabilitystate",
            "b3capabilitystate",
            "b4capabilitystate",
            "b5acapabilitystate",
            "b5bcapabilitystate",
        ]
        for band_capability in band_capabilities:
            attributes.update(
                {
                    band_capability: partial(
                        self.update_band_capability_state,
                        band_name=band_capability,
                    )
                }
            )
        return {**attributes}

    def update_program_track_table_error(self, event: tango.EventData) -> None:
        """
        Updates program track table error

        Args:
            event (tango.EventData): It is the Tango Event Data object

        """
        if event:
            self.current_track_table_error = event
            if self._update_health_state_callback:
                self._update_health_state_callback(HealthState.DEGRADED)
            self.health_manager.update_health_data_and_aggregate(
                {"Calculation_Error": event},
                "ProgramtracktableErrors",
            )

    def update_device_health_state(self, health_state: HealthState) -> None:
        """
        Update a monitored device health state

        :param health_state: health state of the device
        :type health_state: HealthState
        """
        with self.health_state_lock:
            self._device.health_state = health_state
            self._device.last_event_arrived = time.time()

        self.logger.debug(
            "Device %s reported health state %s",
            self._device.dev_name,
            health_state,
        )
        self.health_manager.update_health_data_and_aggregate(
            self._device.health_state, "DishManagerHealthData"
        )

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
                daemon=True,
            )
            self.event_threads.append(thread)
            thread.start()

    def process_event(self, attribute_name):
        with tango.EnsureOmniThread():
            super().process_event(attribute_name)

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

    def update_gpm_data_for_health_aggregation(self) -> None:
        """
        Update health data from component manager.
        """

        self.health_manager.update_health_data_and_aggregate(
            list(self.gpm_validation_result.values()),
            "GPMValidationResultData",
        )

    def update_kvalue_data_for_health_aggregation(self) -> None:
        """
        Update health data from component manager.
        """

        self.health_manager.update_health_data_and_aggregate(
            self.kValueValidationResult,
            "KValueValidationResultData",
        )

    def update_healthinfo_errors(self) -> None:
        """
        Update health info errors from component manager.
        """

        self.health_manager.update_health_data_and_aggregate(
            {None: "No Program Track Table Errors"},
            "ProgramtracktableErrors",
        )

    def update_rxband_health_aggregation(self) -> None:
        """
        Update health data from component manager.
        """

        rb = self.receiver_band

        if rb in (None, ""):
            rb_norm = Band.NONE
        elif isinstance(rb, Band):
            rb_norm = rb
        elif isinstance(rb, int):
            try:
                rb_norm = Band(rb)
            except Exception:
                rb_norm = Band.NONE
        elif isinstance(rb, str) and rb.isdigit():
            try:
                rb_norm = Band(int(rb))
            except Exception:
                rb_norm = Band.NONE
        elif isinstance(rb, str):
            # Accept enum name strings e.g. "B2", "NONE", "UNKNOWN"
            try:
                rb_norm = Band[rb]
            except Exception:
                rb_norm = Band.NONE
        else:
            rb_norm = Band.NONE

        # Keep internal state consistent
        self.receiver_band = rb_norm

        self.health_manager.update_health_data_and_aggregate(
            rb_norm,
            "receiver_band",
        )
