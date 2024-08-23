import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import wait_for_dish_mode


def test_off_command_in_lp(tango_context, cm):
    cm.update_device_dish_mode(DishMode.STANDBY_LP)
    with pytest.raises(CommandNotAllowed):
        cm.is_off_allowed()


def test_off_command_in_fp(tango_context, cm_without_er_lp, task_callback):
    cm = cm_without_er_lp
    wait_for_dish_mode(cm, DishMode.STANDBY_LP)
    cm.is_setstandbyfpmode_allowed()
    cm.setstandbyfpmode(task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    cm.update_device_dish_mode(DishMode.STANDBY_LP)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        }
    )
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_off_allowed()
    cm.off(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    assert wait_for_dish_mode(cm, DishMode.STANDBY_LP)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        }
    )


def test_off_command_adapter_none(cm_without_er_lp, task_callback):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_off_allowed()
    cm.command_timeout = 2
    cm.off(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(status=TaskStatus.COMPLETED)
    assert ResultCode.FAILED == result["result"][0]
    assert "TRANSIENT_NoUsableProfile" in result["result"][1]


def test_off_command_not_allowed(tango_context, cm):
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_off_allowed()
