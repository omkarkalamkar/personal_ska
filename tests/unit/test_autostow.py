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
    tango_context,
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    _simulate_wind_speed(cm, 21.0, 3)
    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    cm.auto_stow.gust_speed_threshold = 10.0
    # updating threshold from 20 to 10
    _simulate_wind_speed(cm, 10.1, 3)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)
    assert cm.gust_wind_speed_mean == 10.1
    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    # updating duration from 3 to 2
    cm.auto_stow.mean_gust_speed_duration = 2.0
    _simulate_wind_speed(cm, 10.1, 2)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)
    assert cm.gust_wind_speed_mean == 10.1
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


def test_wind_ops_auto_stow_completed(
    tango_context,
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    # updating duration from 1000s to 5s
    cm.auto_stow.operational_wind_speed_duration = 5.0
    # FOR UNIT TESTING 5sec is set for wind stow
    _simulate_wind_speed(cm, 10.1, 5)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)

    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    cm.auto_stow.operational_wind_speed_threshold = 12.0
    # updating threshold from 13.5 to 10.0
    _simulate_wind_speed(cm, 12.1, 5)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)
    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)
    assert cm.operational_wind_speed_mean == 12.1


def test_wind_ops_perc_auto_stow_completed(
    tango_context,
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    # attr = {
    #     'SetStowMode.return_value': (
    #         [ResultCode.STARTED],
    #         ["Command Completed"],
    #     ),
    # }
    # dishMock = mock.Mock(**attr)
    # factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    # adapter_factory = mock.Mock(**factory_attrs)
    #
    # cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    # updating duration from 600s to 5s
    cm.auto_stow.operational_perc_mean_diff_duration = 5.0
    # FOR UNIT TESTING 5sec is set for wind stow
    _simulate_wind_speed(cm, 10, 3)
    _simulate_wind_speed(cm, 12, 1)
    _simulate_wind_speed(cm, 20, 1)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)
    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    assert cm.operational_perc_mean_diff > 4.5


def test_wind_auto_stow_completed(
    tango_context,
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    # attr = {
    #     'SetStowMode.return_value': (
    #         [ResultCode.STARTED],
    #         ["Command Completed"],
    #     ),
    # }
    # dishMock = mock.Mock(**attr)
    # factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    # adapter_factory = mock.Mock(**factory_attrs)
    #
    # cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    # updating duration from 600s to 5s
    cm.auto_stow.mean_wind_speed_duration = 5.0
    # FOR UNIT TESTING 5sec is set for wind stow
    _simulate_wind_speed(cm, 13.6, 5)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)

    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    cm.auto_stow.wind_speed_threshold = 10.0
    # updating threshold from 13.5 to 10.0
    _simulate_wind_speed(cm, 10.1, 5)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)
    assert cm.gust_wind_speed_mean == 10.1
    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)


def test_temp_auto_stow_completed(
    tango_context,
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    # attr = {
    #     'SetStowMode.return_value': (
    #         [ResultCode.STARTED],
    #         ["Command Completed"],
    #     ),
    # }
    # dishMock = mock.Mock(**attr)
    # factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    # adapter_factory = mock.Mock(**factory_attrs)

    # cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    _simulate_temp(cm, 41, 1)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)

    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    # update the max threshold
    cm.auto_stow.max_temp_threshold = 25.0
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    _simulate_temp(cm, 25.1, 1)
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
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    # update the min threshold
    cm.auto_stow.min_temp_threshold = -3.0
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    _simulate_temp(cm, -3.1, 1)
    assert wait_for_stow_status(cm, StowStatus.STOW_STARTED)
    simulate_dish_mode_event(cm, DishMode.STOW)
    assert wait_for_dish_mode(cm, DishMode.STOW)
    assert wait_for_stow_status(cm, StowStatus.STOW_COMPLETED)


def test_temp_roc_stow_completed(
    tango_context,
    cm_without_er_lp,
):
    """Testing with time delta of 5s,
    the rate of change of temperature for duration of 5s"""
    cm = cm_without_er_lp
    # attr = {
    #     'SetStowMode.return_value': (
    #         [ResultCode.STARTED],
    #         ["Command Completed"],
    #     ),
    # }
    # dishMock = mock.Mock(**attr)
    # factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    # adapter_factory = mock.Mock(**factory_attrs)
    #
    # cm.adapter_factory = adapter_factory
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


def test_auto_stow_not_invoked(
    tango_context,
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    # attr = {
    #     'SetStowMode.return_value': (
    #         [ResultCode.STARTED],
    #         ["Command Completed"],
    #     ),
    # }
    # dishMock = mock.Mock(**attr)
    # factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    # adapter_factory = mock.Mock(**factory_attrs)
    #
    # cm.adapter_factory = adapter_factory
    cm.weather_station_device_names = ["ska-mid/weather-monitoring/s1"]
    _simulate_wind_speed(cm, 13, 5)  # less than threshold
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    _simulate_wind_speed(cm, 11, 3)  # less than threshold
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    _simulate_temp(cm, 39.9, 1)  # less than threshold
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
    _simulate_temp(cm, -4.9, 1)  # less than threshold
    assert wait_for_stow_status(cm, StowStatus.DISH_NOT_IN_STOW)
