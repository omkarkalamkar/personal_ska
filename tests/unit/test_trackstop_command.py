"""Unit Tests for TrackStop command
"""
import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from tests.settings import create_cm


def test_trackstop_command_completed(
    tango_context, task_callback, dish_master_device
):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.OPERATE)
    assert cm.is_trackstop_allowed()
    cm.trackstop(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


def test_trackstop_command_adapter_none(task_callback, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.OPERATE)
    assert cm.is_trackstop_allowed()
    cm.trackstop(task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, result=ResultCode.FAILED
    )


def test_trackstop_command_not_allowed(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_trackstop_allowed()
