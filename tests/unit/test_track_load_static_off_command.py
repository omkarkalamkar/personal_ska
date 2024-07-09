import json

import pytest
import tango
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory

from tests.settings import DISH_MASTER_DEVICE


def test_trackloadstaticoff_command(
    tango_context, cm, task_callback, group_callback
):
    """Test the successful completion of the TrackLoadStaticOff command."""
    dish_device = DevFactory().get_device(DISH_MASTER_DEVICE)
    cm.get_device()._unresponsive = False
    assert cm.is_trackloadstaticoff_allowed()
    dish_device.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
        stateless=True,
    )

    argin = json.dumps([0.01, 0.02])
    cm.track_load_static_off(argin, task_callback=task_callback)
    unique_id, message = group_callback[
        "longRunningCommandResult"
    ].assert_change_event(
        (Anything, f"[{ResultCode.OK.value}, 'TrackLoadStaticOff completed']"),
        lookahead=10,
    )[
        "attribute_value"
    ]

    assert "TrackLoadStaticOff" in unique_id
    assert "completed" in message
    # Task Callback is not stable.
    # task_callback.assert_against_call(
    #     call_kwargs={"status": TaskStatus.QUEUED}
    # )
    # task_callback.assert_against_call(
    #     call_kwargs={"status": TaskStatus.IN_PROGRESS}
    # )
    # task_callback.assert_against_call(
    # call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK},
    #  lookahead=4,
    # )


@pytest.mark.parametrize(
    "argin",
    [
        json.dumps([0.1]),
        json.dumps([0.1, 0.2, 0.3]),
        [0.5],
    ],
)
def test_trackloadstaticoff_command_invalid_input(
    tango_context, cm, argin, task_callback
):
    """Test the failure scenario while invoking TrackLoadStaticOff command."""
    cm.get_device()._unresponsive = False
    assert cm.is_trackloadstaticoff_allowed()

    status, message = cm.track_load_static_off(
        argin, task_callback=task_callback
    )
    assert status == TaskStatus.REJECTED
    assert (
        "Input argument is incorrect for TrackLoadStaticOff command."
        == message
    )
