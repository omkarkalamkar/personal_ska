import time
from unittest import mock

import pytest
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
    cm: DishLNComponentManager, speed: float, duration: float
):
    start_time = time.time()
    while (time.time() - start_time) < duration:
        cm.update_windspeed(speed, "ska-mid/weather-monitoring/s1")
        time.sleep(1)


def _simulate_temp(
    cm: DishLNComponentManager, temperature: float, duration: float
):
    start_time = time.time()
    while (time.time() - start_time) < duration:
        cm.update_temperature(temperature, "ska-mid/weather-monitoring/s1")
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
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)

    cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    _simulate_wind_speed(cm, 21.0, 3)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)

    # no dishmode stow event
    assert wait_for_stow_status(cm, StowStatus.STOW_FAILED)


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


@pytest.mark.skip(reason="in progress")
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
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)
