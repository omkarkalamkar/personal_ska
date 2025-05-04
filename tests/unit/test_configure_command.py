import json
import time
from unittest import mock

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common import FaultType, PointingState
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import (
    COMMAND_CONFIGURE_BAND_TIMEOUT,
    DISH_MASTER_DEVICE,
    logger,
    simulate_dish_mode_event,
    simulate_result_code_event,
    simulate_track_table_event,
    wait_for_dish_mode,
)


def test_configure_command_completed(
    cm_without_er_lp,
    task_callback,
    json_factory,
):
    cm = cm_without_er_lp

    attr = {
        'SetKValue.return_value': ([ResultCode.OK], ["Command Completed"]),
        'ConfigureBand2.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
        'SetOperateMode.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
        'Track.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
        "GenerateProgramTrackTable.return_value": (ResultCode.STARTED, ""),
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm.adapter_factory = adapter_factory
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    set_kvalue_command = SetKValue(cm, logger=logger)
    set_kvalue_command._adapter_factory = adapter_factory
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK
    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    cm.update_device_configured_band("2")
    simulate_result_code_event(cm, "ConfigureBand2", ResultCode.OK)
    cm.update_device_dish_mode(DishMode.OPERATE)
    simulate_result_code_event(cm, "SetOperateMode", ResultCode.OK)
    simulate_track_table_event(cm)
    cm.update_device_pointing_state(PointingState.TRACK)
    simulate_result_code_event(cm, "Track", ResultCode.OK)
    cm.observable.notify_observers(attribute_value_change=True)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )


def test_configure_command_completed_partial_config(
    cm_without_er_lp, task_callback, json_factory
):
    """Test partial configure functionality"""
    cm = cm_without_er_lp
    attr = {
        'TrackLoadStaticOff.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        )
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm.adapter_factory = adapter_factory
    cm.update_device_dish_mode(DishMode.OPERATE)
    assert wait_for_dish_mode(cm, DishMode.OPERATE)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("partial_configure")

    cm.configure(configure_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    simulate_result_code_event(cm, "TrackLoadStaticOff", ResultCode.OK)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )


def test_delta_configure_command_completed(
    cm_without_er_lp, task_callback, json_factory
):
    """Test that delta configure command completed"""
    cm = cm_without_er_lp
    attr = {
        "GenerateProgramTrackTable.return_value": (ResultCode.STARTED, ""),
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm.adapter_factory = adapter_factory
    cm.update_device_dish_mode(DishMode.OPERATE)
    assert wait_for_dish_mode(cm, DishMode.OPERATE)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("delta_configure")
    primary_configure_input_str = json_factory("dishleafnode_configure_adr106")
    cm.primary_configuration = json.loads(primary_configure_input_str)
    cm.update_device_configured_band("1")
    cm.update_device_pointing_state(PointingState.TRACK)

    cm.configure(configure_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )


# def test_delta_configure_invalid_projection(
#     cm_without_er_lp, task_callback, json_factory
# ):
#     """Test that delta configure command completed"""
#     cm = cm_without_er_lp
#     attr = {
#         "GenerateProgramTrackTable.return_value": (ResultCode.STARTED, ""),
#     }
#     dishMock = mock.Mock(**attr)
#     factory_attrs = {'get_or_create_adapter.return_value': dishMock}
#     adapter_factory = mock.Mock(**factory_attrs)
#     cm.adapter_factory = adapter_factory
#     cm.update_device_dish_mode(DishMode.OPERATE)
#     assert wait_for_dish_mode(cm, DishMode.OPERATE)
#     assert cm.is_configure_allowed()
#     primary_configure_input_str = json_factory("dishleafnode_configure_adr106")
#     cm.primary_configuration = json.loads(primary_configure_input_str)
#     configure_input_str = json_factory("delta_configure")
#     delta_configure = json.loads(configure_input_str)
#     delta_configure["pointing"]["projection"]["alignment"] = "AltAz"
#     res_code, msg = cm.configure(
#         json.dumps(delta_configure), task_callback=task_callback
#     )
#     assert res_code == ResultCode.REJECTED


def test_configure_command_completed_partial_config_missing_key(
    cm_without_er_lp, task_callback, json_factory
):
    """Test partial configure functionality"""
    cm = cm_without_er_lp
    attr = {
        'TrackLoadStaticOff.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        )
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm.adapter_factory = adapter_factory
    cm.update_device_dish_mode(DishMode.OPERATE)
    wait_for_dish_mode(cm, DishMode.OPERATE)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("partial_configure")
    config_json = json.loads(configure_input_str)
    del config_json["pointing"]["target"]["ca_offset_arcsec"]
    configure_input_str = json.dumps(config_json)

    result_code, msg = cm.configure(
        configure_input_str, task_callback=task_callback
    )
    logger.info("Result code %s and msg %s", result_code, msg)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    simulate_result_code_event(cm, "TrackLoadStaticOff", ResultCode.OK)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=7,
    )


@pytest.mark.skip(reason="The scenario is not getting simulated properly")
def test_configure_command_adapter_none(
    task_callback, cm_without_er_lp, json_factory
):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    time.sleep(5)
    result = task_callback.assert_against_call(status=TaskStatus.COMPLETED)
    assert ResultCode.FAILED == result["result"][0]
    assert "TRANSIENT_NoUsableProfile" in result["result"][1]


@pytest.mark.parametrize("key", ["pointing", "dish"])
def test_json_validation(task_callback, cm, json_factory, key):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    config_json = json.loads(configure_input_str)
    del config_json[key]
    configure_input_str = json.dumps(config_json)
    result, message = cm.configure(
        configure_input_str, task_callback=task_callback
    )
    assert result == ResultCode.REJECTED
    assert f"{key} key is not present" in message


def test_configure_command_not_allowed(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_configure_allowed()


def test_configure_command_status_not_allowed(
    cm_without_er_lp,
    task_callback,
    json_factory,
):
    cm = cm_without_er_lp
    attr = {
        'SetKValue.return_value': ([ResultCode.OK], ["Command Completed"]),
        'Configure.return_value': (
            [ResultCode.NOT_ALLOWED],
            ["Command is not allowed"],
        ),
    }
    dishMock = mock.Mock(**attr)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm.adapter_factory = adapter_factory
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    assert wait_for_dish_mode(cm, DishMode.UNKNOWN)
    set_kvalue_command = SetKValue(cm, logger=logger)
    set_kvalue_command._adapter_factory = adapter_factory
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK
    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)
    cm.update_device_configured_band("2")
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        status=TaskStatus.REJECTED,
        result=(ResultCode.NOT_ALLOWED, "Command is not allowed"),
    )


def test_configure_timeout(
    tango_context, cm_without_er_lp, task_callback, json_factory
):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    configure_input_str = json_factory("dishleafnode_configure")

    defect = {
        "enabled": True,
        "fault_type": FaultType.STUCK_IN_INTERMEDIATE_STATE,
        "error_message": "Command stuck in processing",
        "result": ResultCode.FAILED,
        "intermediate_state": PointingState.READY,
    }

    dev_factory = DevFactory()
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)

    assert cm.is_configure_allowed()

    dish_master.SetDefective(json.dumps(defect))
    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    time.sleep(5)
    configure_band_timeout = json.loads(COMMAND_CONFIGURE_BAND_TIMEOUT)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.FAILED, configure_band_timeout[1]),
            "exception": configure_band_timeout[1],
        },
        lookahead=6,
    )
    dish_master.SetDefective(json.dumps({"enabled": False}))
