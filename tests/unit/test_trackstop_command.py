"""Unit Tests for TrackStop command
"""
import threading
import time

import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode, PointingState
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.commands.trackstop_command import TrackStop
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import (
    DISH_MASTER_DEVICE,
    get_mock_adapter_factory,
    simulate_events_on_dish_device,
)


def test_trackstop_command_completed(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    cm.adapter_factory = get_mock_adapter_factory(f"{time.time()}_TrackStop")
    cm.update_device_dish_mode(DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.TRACK)
    assert cm.is_trackstop_allowed()
    track_stop = TrackStop(
        cm, cm.op_state_model, cm.adapter_factory, cm.logger
    )
    simulate_events_on_dish_device(
        cm, [DISH_MASTER_DEVICE], DishMode.OPERATE, cmd_object=track_stop
    )
    track_stop.trackstop(
        task_callback=task_callback, task_abort_event=threading.Event()
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        }
    )


def test_trackstop_command_adapter_none(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.TRACK)
    assert cm.is_trackstop_allowed()
    cm.trackstop(task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(status=TaskStatus.COMPLETED)
    assert ResultCode.FAILED == result["result"][0]
    assert "TRANSIENT_NoUsableProfile" in result["result"][1]


def test_trackstop_command_not_allowed(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_trackstop_allowed()
