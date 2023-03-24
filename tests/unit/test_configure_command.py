import json
import logging
from os.path import dirname, join

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from tests.settings import create_cm, dish_master_device


def get_configure_input_str(
    configure_input_file="dishleafnode_configure.json",
):
    path = join(dirname(__file__), "..", "data", configure_input_file)
    with open(path, "r") as f:
        configure_input_str = f.read()
    return configure_input_str


def test_configure_command_completed(tango_context, task_callback, caplog):
    cm = create_cm(dish_master_device)
    cm._device.dishMode = DishMode.STANDBY_FP
    assert cm.is_configure_allowed()
    configure_input_str = get_configure_input_str()
    configure_input_str = json.loads(configure_input_str)
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


def test_configure_command_adapter_none(
    dish_master_device, task_callback, caplog
):
    cm = create_cm(dish_master_device)
    cm._device.dishMode = DishMode.STANDBY_FP
    assert cm.is_configure_allowed()
    configure_input_str = get_configure_input_str()
    configure_input_str = json.loads(configure_input_str)
    cm.configure(configure_input_str, task_callback=task_callback)
    caplog.set_level(logging.DEBUG, logger="ska_tango_testing.mock")

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
    cm._device.dishMode = DishMode.UNKNOWN
    with pytest.raises(CommandNotAllowed):
        cm.is_configure_allowed()
