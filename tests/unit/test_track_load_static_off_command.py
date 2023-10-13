import json

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common import DeviceUnresponsive

from tests.settings import create_cm


def test_trackloadstaticoff_command(tango_context, dish_master_device, task_callback):
    """Test the successful completion of the TrackLoadStaticOff command."""
    cm = create_cm(dish_master_device)
    assert cm.is_trackloadstaticoff_allowed()

    argin = json.dumps([0.01, 0.02])
    cm.invoke_track_load_static_off(argin, task_callback=task_callback)
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.QUEUED})
    task_callback.assert_against_call(call_kwargs={"status": TaskStatus.IN_PROGRESS})
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


def test_trackloadstaticoff_command_adapter_none(dish_master_device, task_callback):
    """Test the failure scenario while invoking TrackLoadStaticOff command."""
    cm = create_cm(dish_master_device)
    assert cm.is_trackloadstaticoff_allowed()

    argin = json.dumps([0.1])
    status, message = cm.invoke_track_load_static_off(argin, task_callback=task_callback)
    assert status == TaskStatus.REJECTED
    assert "Input argument is incorrect for TrackLoadStaticOff command." == message


def test_trackloadstaticoff_command_not_allowed(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.get_device().update_unresponsive(True)
    with pytest.raises(DeviceUnresponsive):
        cm.is_trackloadstaticoff_allowed()
