import json
from unittest import mock

from ska_tango_base.commands import ResultCode, TaskStatus

from tests.settings import COMMAND_COMPLETION_MESSAGE


def test_apply_pm_setup_command(
    tango_context, cm, json_factory, task_callback
):
    """Test to check the global pointing model command
    functionality"""
    cm.get_device().update_unresponsive(False, "")
    cm.is_ApplyPointingModel_allowed()
    global_pointing_tm_data_path = json_factory("global_pointing_model")
    cm.apply_pm_setup(
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


def test_apply_pm_setup_command_with_faulty_path(
    tango_context, cm, json_factory, task_callback
):
    """
    This test verifies the command gets rejected when faulty TmData path
    gets detected.
    """
    cm.get_device().update_unresponsive(False, "")
    cm.is_ApplyPointingModel_allowed()
    global_pointing_tm_model_path = json_factory("global_pointing_model")
    global_pointing_tm_model_path = json.loads(global_pointing_tm_model_path)
    global_pointing_tm_model_path["tm_data_sources"] = "abc"
    cm.apply_pm_setup(
        json.dumps(global_pointing_tm_model_path), task_callback=task_callback
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )

    call_args = task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": mock.ANY,
            "exception": mock.ANY,
        }
    )
    assert (
        "Error in Loading global pointing data"
        in call_args["call_kwargs"]["result"][1]
    )
    assert "Error in Loading global pointing data" in str(
        call_args["call_kwargs"]["exception"]
    )


def test_apply_pm_setup_command_with_faulty_json(
    tango_context, cm, json_factory, task_callback
):
    """
    This test verifies the command gets rejected when faulty TmData path
    gets detected.
    """
    cm.get_device().update_unresponsive(False, "")
    cm.is_ApplyPointingModel_allowed()
    global_pointing_tm_model_path = json_factory(
        "global_pointing_model_faulty"
    )
    global_pointing_tm_model_path = json.loads(global_pointing_tm_model_path)
    cm.apply_pm_setup(
        json.dumps(global_pointing_tm_model_path), task_callback=task_callback
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )

    call_args = task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": mock.ANY,
            "exception": mock.ANY,
        }
    )
    assert "JSON Error" in call_args["call_kwargs"]["result"][1]
    assert "JSON Error" in str(call_args["call_kwargs"]["exception"])


def test_apply_pm_setup_command_with_wrong_dish_id(
    tango_context, cm, json_factory, task_callback
):
    """
    This test verifies the command gets rejected when faulty TmData path
    gets detected.
    """
    cm.get_device().update_unresponsive(False, "")
    cm.is_ApplyPointingModel_allowed()
    global_pointing_tm_model_path = json_factory(
        "global_pointing_model_ska002"
    )
    global_pointing_tm_model_path = json.loads(global_pointing_tm_model_path)
    cm.apply_pm_setup(
        json.dumps(global_pointing_tm_model_path), task_callback=task_callback
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )

    call_args = task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": mock.ANY,
            "exception": mock.ANY,
        }
    )
    assert "SKA002 is not matching" in call_args["call_kwargs"]["result"][1]
    assert "SKA002 is not matching" in str(
        call_args["call_kwargs"]["exception"]
    )
