import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from tests.settings import create_cm


def test_off_command_in_lp(tango_context, dish_master_device, task_callback):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.STANDBY_LP)
    assert cm.is_off_allowed()

    cm.off(task_callback=task_callback)
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(status=TaskStatus.COMPLETED, result=ResultCode.OK)


def test_off_command_in_fp(tango_context, dish_master_device, task_callback):
    cm = create_cm(dish_master_device)
    cm.setstandbyfpmode(task_callback)
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )
    assert cm.is_off_allowed()

    cm.off(task_callback=task_callback)
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(status=TaskStatus.COMPLETED, result=ResultCode.OK)


def test_off_command_adapter_none(dish_master_device, task_callback):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_off_allowed()
    cm.command_timeout = 2
    cm.off(task_callback=task_callback)
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED,
        result=ResultCode.FAILED,
        exception="Timeout occurred while invoking the SetStandbyLPMode Command.",
    )


def test_off_command_not_allowed(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_off_allowed()
