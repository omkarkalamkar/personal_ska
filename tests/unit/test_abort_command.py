"""Unit tests for Abort command"""
import threading
import time

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DishMode

from ska_tmc_dishleafnode.commands.abort_command import Abort
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import (
    get_mock_adapter_factory,
    logger,
    simulate_events_on_dish_device,
)


def test_abort_command(cm_without_er_lp, task_callback):
    cm = cm_without_er_lp
    command_id = f"{time.time()}_Abort"
    adapter_factory = get_mock_adapter_factory(command_id)
    abort_command = Abort(cm, cm.op_state_model, adapter_factory, logger)
    simulate_events_on_dish_device(
        cm,
        ["mid-dish/dish-manager/ska001"],
        DishMode.STANDBY_FP,
        cmd_object=abort_command,
    )
    abort_command.invoke_abort(
        task_callback=task_callback, task_abort_event=threading.Event()
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.IN_PROGRESS,
        },
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
    )


def test_cm_abort(cm_without_er_lp, task_callback):
    task_status, message = cm_without_er_lp.abort(task_callback=task_callback)
    assert task_status == TaskStatus.IN_PROGRESS
    assert message == "Aborting tasks"
