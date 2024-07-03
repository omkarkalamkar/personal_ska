import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE


def test_scan_command(tango_context, cm, task_callback):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_scan_allowed()

    cm.scan("1", task_callback=task_callback)
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


def test_scan_command_adapter_none(cm_without_er_lp, task_callback):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_scan_allowed()

    cm.scan("1", task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED,
        result=(
            ResultCode.FAILED,
            "DevFailed[\n"
            "DevError[\n"
            "    desc = TRANSIENT CORBA system exception:"
            + " TRANSIENT_NoUsableProfile\n"
            "  origin = void Tango::Connection::connect(const string&) at"
            + " (/src/cppTango/src/client/devapi_base.cpp:609)\n"
            "  reason = API_CorbaException\n"
            "severity = ERR]\n\n"
            "DevError[\n"
            "    desc = Failed to connect to database on host tango-databaseds"
            + " with port 10000\n"
            "  origin = void Tango::Connection::connect(const string&) at"
            + " (/src/cppTango/src/client/devapi_base.cpp:609)\n"
            "  reason = API_CantConnectToDatabase\n"
            "severity = ERR]\n"
            "]",
        ),
    )


def test_scan_mode_command_not_allowed(tango_context, cm):
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_scan_allowed()
