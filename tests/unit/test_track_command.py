"""Unit Tests for Track command
"""
from os.path import dirname, join

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode, PointingState
from ska_tmc_common.exceptions import CommandNotAllowed


def get_track_input_str(
    track_input_file="dishleafnode_track.json",
):
    path = join(dirname(__file__), "..", "data", track_input_file)
    with open(path, "r") as f:
        config_str = f.read()
    return config_str


def test_track_command_completed(tango_context, task_callback, cm):
    cm.update_device_dish_mode(DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.READY)
    assert cm.is_track_allowed()
    track_input_str = get_track_input_str()
    cm.track(track_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": ResultCode.QUEUED,
        }
    )


def test_track_command_adapter_none(task_callback, cm):
    cm.update_device_dish_mode(DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.READY)
    assert cm.is_track_allowed()
    track_input_str = get_track_input_str()
    cm.track(track_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, result=ResultCode.FAILED
    )


def test_json_validation(tango_context, task_callback, cm):
    cm.update_device_dish_mode(DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.READY)
    assert cm.is_track_allowed()
    track_input_str = get_track_input_str("invalid_key_track.json")
    result, message = cm.track(track_input_str, task_callback=task_callback)
    assert result == ResultCode.FAILED
    assert "key is not present" in message


def test_track_command_not_allowed(tango_context, cm):
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_track_allowed()
