import time

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from tests.settings import create_cm


@pytest.mark.long_running
def test_setstandbylpmode_command(
    tango_context, dish_master_device, task_callback
):
    cm = create_cm(dish_master_device)
    assert cm.is_command_allowed("SetStandbyLPMode")

    cm.setstandbylpmode(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    time.sleep(0.1)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


@pytest.mark.long_running
def test_setstandbylpmode_command_adapter_none(
    tango_context, dish_master_device, task_callback
):
    cm = create_cm(dish_master_device)
    cm.timeout = 0
    assert cm.is_command_allowed("SetStandbyLPMode")

    cm.setstandbylpmode(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    time.sleep(0.1)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.FAILED,
            "result": ResultCode.FAILED,
            "exception": "Error in creating adapter for Dish Master: Adapter is None",  # noqa:E501
        }
    )


@pytest.mark.long_running
def test_setstandbylpmode_command_not_allowed(
    tango_context, dish_master_device
):
    cm = create_cm(dish_master_device)
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("SetStandbyLPMode")
