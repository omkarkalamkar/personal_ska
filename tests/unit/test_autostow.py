import time
from unittest import mock

from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode

from ska_tmc_dishleafnode.enums.stow_status import StowStatus
from ska_tmc_dishleafnode.manager.component_manager import (
    DishLNComponentManager,
)
from tests.settings import (
    simulate_dish_mode_event,
    wait_for_dish_mode,
    wait_for_stow_status,
)


def _simulate_wind_speed(
    cm_without_er_lp: DishLNComponentManager, speed: float, duration: float
):
    start_time = time.time()
    while (time.time() - start_time) < duration:
        cm_without_er_lp.update_windspeed(
            speed, "ska-mid/weather-monitoring/s1"
        )
        time.sleep(1)


def _simulate_temp(
    cm_without_er_lp: DishLNComponentManager,
    temperature: float,
    duration: float,
):
    start_time = time.time()
    while (time.time() - start_time) < duration:
        cm_without_er_lp.update_temperature(
            temperature, "ska-mid/weather-monitoring/s1"
        )
        time.sleep(1)


def test_gust_auto_stow_completed(
    cm_without_er_lp,
):
    cm = cm_without_er_lp

    attr = {
        'SetStowMode.return_value': (
            [ResultCode.STARTED],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    _simulate_wind_speed(cm, 21.0, 3)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)
    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)


def test_gust_auto_stow_failed(
    cm_without_er_lp,
):
    cm = cm_without_er_lp

    attr = {
        'SetStowMode.return_value': (
            [ResultCode.STARTED],
            ["Command Completed"],
        ),
        'StopProgramTrackTable.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
    }
    cm.command_timeout = 5
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)

    cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    _simulate_wind_speed(cm, 21.0, 3)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)

    # no dishmode stow event
    assert wait_for_stow_status(cm, StowStatus.STOW_FAILED, timeout=6)


def test_wind_auto_stow_completed(
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    attr = {
        'SetStowMode.return_value': (
            [ResultCode.STARTED],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)

    cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    # FOR UNIT TESTING 5sec is set for wind stow
    _simulate_wind_speed(cm, 13.5, 5)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)

    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)


def test_temp_auto_stow_completed(
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    attr = {
        'SetStowMode.return_value': (
            [ResultCode.STARTED],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)

    cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    _simulate_temp(cm, 41, 1)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)

    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    _simulate_temp(cm, -5.1, 1)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)

    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)


def test_temp_roc_stow_completed(
    cm_without_er_lp,
):
    """Testing with time delta of 5s,
    the rate of change of temperature for duration of 5s"""
    cm = cm_without_er_lp
    attr = {
        'SetStowMode.return_value': (
            [ResultCode.STARTED],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)

    cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    cm.auto_stow.time_delta = 5  # 5 seconds
    # simulate such that the temp delta in 5seconds is more than 4.5
    _simulate_temp(cm, 20, 1)
    # delibrately making keep it same to check the rate of change from
    # the next second
    _simulate_temp(cm, 20, 1)
    _simulate_temp(cm, 21, 1)
    _simulate_temp(cm, 22, 1)
    _simulate_temp(cm, 23, 1)
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    _simulate_temp(cm, 26, 1)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)

    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)


def test_temp_auto_stow_not_invoked(
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    attr = {
        'SetStowMode.return_value': (
            [ResultCode.STARTED],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)

    cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    _simulate_wind_speed(cm, 13, 5)  # less than threshold
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    _simulate_wind_speed(cm, 11, 3)  # less than threshold
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    _simulate_temp(cm, 39.9, 1)  # less than threshold
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    _simulate_temp(cm, -4.9, 1)  # less than threshold
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
