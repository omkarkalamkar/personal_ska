"""Unit Tests for Track command
"""

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE


def test_configure_band_command_completed(
    tango_context, task_callback, cm, group_callback
):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configureband_allowed()

    receiver_band = "1"
    cm.configureband(receiver_band, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
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


def test_configureband_command_adapter_none(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configureband_allowed()

    receiver_band = "1"
    cm.configureband(receiver_band, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(status=TaskStatus.COMPLETED)
    assert ResultCode.FAILED == result["result"][0]
    assert "TRANSIENT_NoUsableProfile" in result["result"][1]


def test_configureband_command_not_allowed(tango_context, cm):
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_configureband_allowed()
