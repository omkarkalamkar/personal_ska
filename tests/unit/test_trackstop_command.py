"""Unit Tests for TrackStop command
"""
from unittest import mock

import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode, PointingState
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import simulate_result_code_event


def test_trackstop_command_completed(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    attrs = {
        'TrackStop.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(
        **attrs,
    )
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm.adapter_factory = adapter_factory
    cm.update_device_dish_mode(DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.TRACK)
    assert cm.is_trackstop_allowed()
    cm.trackstop(task_callback=task_callback)
    # task_callback.assert_against_call(
    #     call_kwargs={"status": TaskStatus.QUEUED}
    # )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    simulate_result_code_event(cm, "TrackStop", ResultCode.OK)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        }
    )


@pytest.mark.test_trstp_n
def test_trackstop_command_adapter_none(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.TRACK)
    assert cm.is_trackstop_allowed()
    cm.trackstop(task_callback=task_callback)

    # task_callback.assert_against_call(
    #     call_kwargs={"status": TaskStatus.QUEUED}
    # )
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
