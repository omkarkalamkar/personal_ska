import json
from os.path import dirname, join

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from tests.settings import create_cm


def get_configure_input_str(
    configure_input_file="dishleafnode_configure.json",
):
    path = join(dirname(__file__), "..", "data", configure_input_file)
    with open(path, "r") as f:
        config_str = f.read()
    return json.loads(config_str)


def test_configure_command_completed(
    tango_context, task_callback, dish_master_device
):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = get_configure_input_str()
    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


def test_configure_command_adapter_none(task_callback, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = get_configure_input_str()
    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, result=ResultCode.FAILED
    )


def test_configure_command_not_allowed(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_configure_allowed()
