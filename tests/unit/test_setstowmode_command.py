import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from tests.settings import create_cm


@pytest.mark.stow
def test_setstowmode_command(tango_context, dish_master_device, task_callback):
    cm = create_cm(dish_master_device)
    assert cm.is_command_allowed("SetStowMode")

    cm.setstowmode(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


@pytest.mark.stow
def test_setstowmode_command_adapter_none(tango_context, task_callback):
    device_not_in_db = "mid_d0002/elt/master"
    cm = create_cm(device_not_in_db)
    message = f"""Error in creating adapter for {device_not_in_db}: DevFailed[
DevError[
    desc = OBJECT_NOT_EXIST CORBA system exception: OBJECT_NOT_EXIST_NoMatch
  origin = Connection::connect
  reason = API_CorbaException
severity = ERR]

DevError[
    desc = Failed to connect to device {device_not_in_db}
  origin = Connection::connect
  reason = API_DeviceNotDefined
severity = ERR]
]"""
    assert cm.is_command_allowed("SetStowMode")

    cm.setstowmode(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": ResultCode.FAILED,
            "exception": message,
        }
    )


@pytest.mark.stow
def test_setstowmode_command_not_allowed(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("SetStowMode")
