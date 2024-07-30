import json
from unittest import mock

from ska_tango_base.commands import ResultCode, TaskStatus

from tests.settings import COMMAND_COMPLETION_MESSAGE


def test_static_pm_setup_command(
    tango_context, cm, json_factory, task_callback
):
    """Test to check the global pointing model command
    functionality"""

    cm.is_staticpmsetup_allowed()
    global_pointing_tm_data_path = json_factory("global_pointing_model")
    cm.static_pm_setup(
        global_pointing_tm_data_path, task_callback=task_callback
    )

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


def test_static_pm_setup_command_with_faulty_path(
    tango_context, cm, json_factory, task_callback
):
    """
    This test verifies the command gets rejected when faulty TmData path
    gets detected.
    """
    cm.is_staticpmsetup_allowed()
    global_pointing_tm_model_path = json_factory("global_pointing_model")
    global_pointing_tm_model_path = json.loads(global_pointing_tm_model_path)
    global_pointing_tm_model_path["tm_data_sources"] = "abc"
    cm.static_pm_setup(
        json.dumps(global_pointing_tm_model_path), task_callback=task_callback
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )

    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.REJECTED, "Error in TelModel path"),
            "exception": mock.ANY,
        }
    )
