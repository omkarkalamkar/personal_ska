import time
from unittest import mock

import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.commands.setstowmode import SetStowMode
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import (
    DISH_MASTER_DEVICE,
    get_mock_adapter_factory,
    simulate_events_on_dish_device,
)


def test_setstowmode_command(cm_without_er_lp, task_callback):
    cm = cm_without_er_lp
    command_id = f"{time.time()}_SetStowMode"
    cm.adapter_factory = get_mock_adapter_factory(command_id)
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_setstowmode_allowed()
    set_stow_mode = SetStowMode(
        cm, cm.op_state_model, cm.adapter_factory, cm.logger
    )
    simulate_events_on_dish_device(
        cm, [DISH_MASTER_DEVICE], DishMode.STOW, cmd_object=set_stow_mode
    )
    set_stow_mode.invoke_set_stow_mode(
        task_callback=task_callback, task_abort_event=mock.MagicMock()
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=5,
    )


def test_setstowmode_command_adapter_none(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_setstowmode_allowed()

    cm.setstowmode(task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, lookahead=5
    )
    assert ResultCode.FAILED == result["result"][0]
    assert "TRANSIENT_NoUsableProfile" in result["result"][1]


def test_setstowmode_command_not_allowed(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_setstowmode_allowed()
