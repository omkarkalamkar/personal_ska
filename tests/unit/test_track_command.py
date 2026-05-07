"""Unit Tests for Track command
"""
import threading
import time
from os.path import dirname, join

import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode, PointingState
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.commands.track_command import Track
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import (
    DISH_MASTER_DEVICE,
    get_mock_adapter_factory,
    simulate_events_on_dish_device,
)


def get_track_input_str(
    track_input_file="dishleafnode_track.json",
):
    path = join(dirname(__file__), "..", "data", track_input_file)
    with open(path, "r") as f:
        config_str = f.read()
    return config_str


def test_track_command_completed(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    command_id = f"{time.time()}_Track"
    cm.adapter_factory = get_mock_adapter_factory(command_id)
    track_input_str = get_track_input_str()
    cm.update_device_dish_mode(DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.READY)
    cm.is_track_allowed()
    track_obj = Track(cm, cm.op_state_model, cm.adapter_factory, cm.logger)
    simulate_events_on_dish_device(
        cm, [DISH_MASTER_DEVICE], DishMode.OPERATE, cmd_object=track_obj
    )
    track_obj.track(
        track_input_str,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )


def test_track_command_adapter_none(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.READY)
    assert cm.is_track_allowed()
    track_input_str = get_track_input_str()
    cm.track(track_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, lookahead=2
    )
    assert ResultCode.FAILED == result["result"][0]
    assert "TRANSIENT_NoUsableProfile" in result["result"][1]


def test_json_validation(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.READY)
    assert cm.is_track_allowed()
    track_input_str = get_track_input_str("invalid_key_track.json")
    result, message = cm.track(track_input_str, task_callback=task_callback)
    assert result == ResultCode.FAILED
    assert "key is not present" in message


def test_track_command_not_allowed(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_track_allowed()
