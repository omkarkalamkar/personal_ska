import json
import time

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import (
    logger,
    simulate_result_code_event,
    wait_for_dish_mode,
)


def test_configure_command_completed(
    tango_context,
    cm,
    task_callback,
    json_factory,
):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()

    set_kvalue_command = SetKValue(cm, logger=logger)
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK

    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)
    time.sleep(0.5)
    cm.update_device_configured_band("2")
    time.sleep(0.5)
    cm.update_device_dish_mode(DishMode.OPERATE)
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
    time.sleep(1)
    simulate_result_code_event(cm, "TrackLoadStaticOff", ResultCode.OK)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )


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
    time.sleep(1)
    simulate_result_code_event(cm, "TrackLoadStaticOff", ResultCode.OK)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=12,
    )


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


def test_json_validation(tango_context, task_callback, cm, json_factory):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    config_json = json.loads(configure_input_str)
    del config_json["dish"]
    configure_input_str = json.dumps(config_json)
    result, message = cm.configure(
        configure_input_str, task_callback=task_callback
    )
    assert result == ResultCode.FAILED
    assert "dish key is not present" in message


def test_json_validation_pointing_doesnot_exist(
    tango_context, task_callback, cm, json_factory
):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    config_json = json.loads(configure_input_str)
    del config_json["pointing"]
    configure_input_str = json.dumps(config_json)
    result, message = cm.configure(
        configure_input_str, task_callback=task_callback
    )
    assert result == ResultCode.REJECTED
    assert "Correction key 'pointing' does not exist" in message


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


@pytest.mark.parametrize("correction", ["UPDATE", "RESET", "MAINTAIN"])
def test_configure_command_completed_with_correction_key(
    tango_context,
    cm,
    task_callback,
    json_factory,
    correction,
):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()

    set_kvalue_command = SetKValue(cm, logger=logger)
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK

    configure_input_str = json_factory("dishleafnode_configure")
    configure_input_str = json.loads(configure_input_str)
    configure_input_str["pointing"]["correction"] = correction
    configure_input_str = json.dumps(configure_input_str)
    cm.configure(configure_input_str, task_callback=task_callback)
    time.sleep(0.5)
    cm.update_device_configured_band("2")
    time.sleep(0.5)
    cm.update_device_dish_mode(DishMode.OPERATE)
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
