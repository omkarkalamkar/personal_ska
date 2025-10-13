import json
from unittest import mock

from ska_tango_base.commands import ResultCode, TaskStatus

from ska_tmc_dishleafnode.commands.apply_pointing_model import (
    ApplyPointingModel,
)

interface = "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0"
data_sources = [
    "car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators?1.0.0#tmdata"
]
file_path = (
    "instrument/ska_mid1/global_pointing_model_data/gpm-ska093-Band_2.json"
)


def test_apply_pointing_model_command(
    tango_context, cm_without_er_lp, json_factory, task_callback
):
    """Test to check the global pointing model command
    functionality"""
    cm = cm_without_er_lp
    cm.get_device().update_unresponsive(False, "")
    cm.is_apply_pointing_model_allowed()
    global_pointing_tm_data_path = json_factory("global_pointing_model")
    cm.apply_pointing_model(
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
            "result": (
                ResultCode.OK,
                "Successfully wrote the GPM values",
            ),
        },
    )


def test_apply_pointing_model_command_with_faulty_path(
    tango_context, cm_without_er_lp, json_factory, task_callback
):
    """
    This test verifies the command gets rejected when faulty TmData path
    gets detected.
    """
    cm = cm_without_er_lp
    cm.get_device().update_unresponsive(False, "")
    cm.is_apply_pointing_model_allowed()
    global_pointing_tm_model_path = json_factory("global_pointing_model")
    global_pointing_tm_model_path = json.loads(global_pointing_tm_model_path)
    global_pointing_tm_model_path["tm_data_sources"] = "abc"
    cm.apply_pointing_model(
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
        },
        lookahead=2,
    )
    assert (
        "Error in loading global pointing data"
        in call_args["call_kwargs"]["result"][1]
    )
    assert "Error in loading global pointing data" in str(
        call_args["call_kwargs"]["exception"]
    )


def test_apply_pointing_model_command_with_faulty_json(
    tango_context, cm_without_er_lp, json_factory, task_callback
):
    """
    This test verifies the command gets rejected when faulty TmData path
    gets detected.
    """
    cm = cm_without_er_lp
    cm.get_device().update_unresponsive(False, "")
    cm.is_apply_pointing_model_allowed()
    global_pointing_tm_model_path = json_factory(
        "global_pointing_model_faulty"
    )
    global_pointing_tm_model_path = json.loads(global_pointing_tm_model_path)
    cm.apply_pointing_model(
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
        },
        lookahead=2,
    )
    assert "JSON Error" in call_args["call_kwargs"]["result"][1]
    assert "JSON Error" in str(call_args["call_kwargs"]["exception"])


def test_apply_pointing_model_command_file_not_found(
    tango_context, cm_without_er_lp, task_callback
):
    """
    This test verifies the command gets failed when file not
    found on the repo.
    """
    cm = cm_without_er_lp
    cm.get_device().update_unresponsive(False, "")
    cm.is_apply_pointing_model_allowed()
    gpm_json = json.dumps(
        {
            "interface": interface,
            "tm_data_sources": data_sources,
            "tm_data_filepath": file_path,
        }
    )
    cm.apply_pointing_model(gpm_json, task_callback=task_callback)

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
        },
        lookahead=2,
    )
    assert "not found" in call_args["call_kwargs"]["result"][1]
    assert "not found" in str(call_args["call_kwargs"]["exception"])


def test_apm_extract_band_version(cm_without_er_lp):
    """Test to check the extract band and version method"""
    cm = cm_without_er_lp
    for band, _ in cm.gpm_version.items():
        assert cm.gpm_version[band] == "UNKNOWN"
    gpm_json = {
        "interface": interface,
        "tm_data_sources": data_sources,
        "tm_data_filepath": file_path,
    }
    adapter_factory = mock.MagicMock()
    logger = mock.MagicMock()
    op_state_model = mock.MagicMock()

    apm_command = ApplyPointingModel(
        cm,
        op_state_model=op_state_model,
        adapter_factory=adapter_factory,
        logger=logger,
    )
    band, band_version = apm_command.extract_band_and_version(
        gpm_data=gpm_json
    )
    assert band == 'Band_2'
    assert band_version == '1.0.0'
