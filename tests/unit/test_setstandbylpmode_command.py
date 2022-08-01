import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from tests.settings import create_cm


def test_setstandbylpmode_command(
    tango_context, dish_master_device, task_callback
):
    cm = create_cm(dish_master_device)
    assert cm.is_command_allowed("SetStandbyLPMode")

    cm.setstandbylpmode(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


def test_setstandbylpmode_command_adapter_none(
    dish_master_device, task_callback
):
    cm = create_cm(dish_master_device)
    assert cm.is_command_allowed("SetStandbyLPMode")

    cm.setstandbylpmode(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback_signature = task_callback.assert_against_call()
    task_callback_signature["call_kwargs"]["status"] = TaskStatus.COMPLETED
    task_callback_signature["call_kwargs"]["result"] = ResultCode.FAILED


def test_setstandbylpmode_command_not_allowed(
    tango_context, dish_master_device
):
    cm = create_cm(dish_master_device)
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("SetStandbyLPMode")
