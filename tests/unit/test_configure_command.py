import json
from os.path import dirname, join

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from tests.settings import create_cm, logger, wait_for_dish_mode


def get_configure_input_str(
    configure_input_file="dishleafnode_configure.json",
):
    path = join(dirname(__file__), "..", "data", configure_input_file)
    with open(path, "r") as f:
        config_str = f.read()
    return json.dumps(config_str)


def test_configure_command_completed(tango_context, task_callback, dish_master_device):
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
    configure_input_str = get_configure_input_str()
    cm.configure(configure_input_str, task_callback=task_callback)
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


def test_configure_command_completed_partial_config(
    tango_context, task_callback, dish_master_device
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
    configure_input_str = get_configure_input_str("partial_configure.json")
    logger.info("The input json string is -> %s", configure_input_str)
    cm.configure(configure_input_str, task_callback=task_callback)
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


def test_configure_command_adapter_none(task_callback, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = get_configure_input_str()
    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(status=TaskStatus.COMPLETED, result=ResultCode.FAILED)


def test_json_validation(tango_context, task_callback, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = get_configure_input_str("invalid_key.json")
    result, message = cm.configure(configure_input_str, task_callback=task_callback)
    assert result == ResultCode.FAILED
    assert "key is not present" in message


def test_configure_command_not_allowed(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_configure_allowed()
