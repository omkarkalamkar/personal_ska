import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed


def test_set_operate_command(tango_context, cm, task_callback):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_setoperatemode_allowed()

    cm.setoperatemode(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


@pytest.mark.skip("Will be resolved as a part of HM-461")
def test_set_operate_command_adapter_none(task_callback, cm):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_setoperatemode_allowed()

    cm.setoperatemode(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, result=ResultCode.FAILED
    )


def test_set_operate_mode_command_not_allowed(tango_context, cm):
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_setoperatemode_allowed()
