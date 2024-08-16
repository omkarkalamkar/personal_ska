import json
import time

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common import FaultType, PointingState
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import (
    DISH_MASTER_DEVICE,
    logger,
    simulate_result_code_event,
    wait_for_dish_mode,
)


def test_configure_command_completed(
    tango_context, cm, task_callback, json_factory, dish_master_device
):
    dev_factory = DevFactory()
    dish_device = dev_factory.get_device(dish_master_device)
    dish_device.SetDirectDishMode(DishMode.STANDBY_FP)
    time.sleep(0.2)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    set_kvalue_command = SetKValue(cm, logger=logger)
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK
    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)
    dish_device.programTrackTable = [
        775853423.2247269,
        178.758613204265,
        31.165682681453,
    ]
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
        }
    )
    cm.set_track_process_event()
    cm.stop_track_table_process()


def test_configure_command_completed_partial_config(
    tango_context, cm_without_er_lp, task_callback, json_factory
):
    """Test partial configure functionality"""
    cm = cm_without_er_lp
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
    time.sleep(5)
    simulate_result_code_event(cm, "TrackLoadStaticOff", ResultCode.OK)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )
    cm.set_track_process_event()
    cm.stop_track_table_process()


def test_configure_command_completed_partial_config_missing_key(
    tango_context, cm_without_er_lp, task_callback, json_factory
):
    """Test partial configure functionality"""
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.OPERATE)
    wait_for_dish_mode(cm, DishMode.OPERATE)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("partial_configure")
    config_json = json.loads(configure_input_str)
    del config_json["pointing"]["target"]["ca_offset_arcsec"]
    configure_input_str = json.dumps(config_json)

    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    time.sleep(5)
    simulate_result_code_event(cm, "TrackLoadStaticOff", ResultCode.OK)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=12,
    )
    cm.set_track_process_event()
    cm.stop_track_table_process()


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
    result = task_callback.assert_against_call(status=TaskStatus.COMPLETED)
    assert ResultCode.FAILED == result["result"][0]
    assert "TRANSIENT_NoUsableProfile" in result["result"][1]


@pytest.mark.parametrize("key", ["pointing", "dish"])
def test_json_validation(tango_context, task_callback, cm, json_factory, key):
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
    assert result == ResultCode.FAILED
    assert f"{key} key is not present" in message


def test_configure_command_not_allowed(tango_context, cm):
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_configure_allowed()


def test_configure_command_status_not_allowed(
    tango_context,
    cm,
    task_callback,
    json_factory,
):
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    assert wait_for_dish_mode(cm, DishMode.UNKNOWN)
    set_kvalue_command = SetKValue(cm, logger=logger)
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK
    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)
    time.sleep(0.5)
    cm.update_device_configured_band("2")
    time.sleep(0.5)
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        status=TaskStatus.REJECTED,
        result=(ResultCode.NOT_ALLOWED, "Command is not allowed"),
    )


def test_configure_timeout(tango_context, cm, task_callback, json_factory):
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
    message = (
        "Timeout occurred while waiting for 2 configuredBand in "
        + "Configure command."
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.FAILED, message),
            "exception": message,
        }
    )
    dish_master.SetDefective(json.dumps({"enabled": False}))
