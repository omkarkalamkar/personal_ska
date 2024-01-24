import json

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus

from tests.settings import create_cm


def test_trackloadstaticoff_command(tango_context, dish_master_device, task_callback):
    """Test the successful completion of the TrackLoadStaticOff command."""
    cm = create_cm(dish_master_device)
    assert cm.is_trackloadstaticoff_allowed()

    argin = json.dumps([0.01, 0.02])
    cm.track_load_static_off(argin, task_callback=task_callback)
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}, lookahead=4
    )


@pytest.mark.parametrize(
    "argin",
    [
        json.dumps([0.1]),
        json.dumps([0.1, 0.2, 0.3]),
        [0.5],
    ],
)
def test_trackloadstaticoff_command_invalid_input(
    tango_context, dish_master_device, argin, task_callback
):
    """Test the failure scenario while invoking TrackLoadStaticOff command."""
    cm = create_cm(dish_master_device)
    assert cm.is_trackloadstaticoff_allowed()

    status, message = cm.track_load_static_off(argin, task_callback=task_callback)
    assert status == TaskStatus.REJECTED
    assert "Input argument is incorrect for TrackLoadStaticOff command." == message
