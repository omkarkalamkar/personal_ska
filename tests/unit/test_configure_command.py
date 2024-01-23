import json

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from tests.settings import create_cm, wait_for_dish_mode


def test_configure_command_completed(
    tango_context, task_callback, dish_master_device, json_factory
):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.STANDBY_LP)
    cm.is_setstandbyfpmode_allowed()
    cm.setstandbyfpmode(task_callback)
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


def test_configure_command_completed_partial_config(
    tango_context, task_callback, dish_master_device, json_factory
):
    """Test partial configure functionality"""
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.OPERATE)

    assert cm.is_configure_allowed()
    configure_input_str = json_factory("partial_configure")

    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}, lookahead=5
    )


def test_configure_command_completed_partial_config_missing_key(
    tango_context, task_callback, dish_master_device, json_factory
):
    """Test partial configure functionality"""
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.OPERATE)

    assert cm.is_configure_allowed()
    configure_input_str = json_factory("partial_configure")
    config_json = json.loads(configure_input_str)
    del config_json["pointing"]["target"]["ca_offset_arcsec"]
    configure_input_str = json.dumps(config_json)

    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


def test_configure_command_adapter_none(task_callback, dish_master_device, json_factory):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(status=TaskStatus.COMPLETED, result=ResultCode.FAILED)


@pytest.mark.parametrize("key", ["pointing", "dish"])
def test_json_validation(tango_context, task_callback, dish_master_device, json_factory, key):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    config_json = json.loads(configure_input_str)
    del config_json[key]
    configure_input_str = json.dumps(config_json)
    result, message = cm.configure(configure_input_str, task_callback=task_callback)
    assert result == ResultCode.FAILED
    assert f"{key} key is not present" in message


def test_configure_command_not_allowed(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_configure_allowed()
