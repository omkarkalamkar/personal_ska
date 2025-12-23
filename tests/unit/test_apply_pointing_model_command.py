import json
from unittest import mock
from unittest.mock import MagicMock, patch

import numpy as np
import tango
from ska_tango_base.commands import ResultCode, TaskStatus

from ska_tmc_dishleafnode.commands.apply_pointing_model import (
    ApplyPointingModel,
)
from ska_tmc_dishleafnode.manager.event_receiver import DishLNEventReceiver
from ska_tmc_dishleafnode.manager.gpm_validator import GPMValidator

interface = "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0"
data_sources = [
    "car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators?1.0.0#tmdata"
]
file_path = (
    "instrument/ska_mid1/global_pointing_model_data/gpm-ska093-Band_2.json"
)
dish_param = [
    -491.0523681640625,
    -46.494388580322266,
    -0.20043884217739105,
    6.303488731384277,
    7.303488731384277,
    16.015695571899414,
    3.3034884929656982,
    11.97440242767334,
    -3.738542079925537,
    8.303488731384277,
    2.3034884929656982,
    1655.9869384765625,
    -145.2842254638672,
    -26.760848999023438,
    2.3034884929656982,
    7.303488731384277,
    5.303488731384277,
    1.3034884929656982,
]


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
    adapter_factory = MagicMock()
    logger = MagicMock()
    op_state_model = MagicMock()

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


def test_to_check_apm_command_successful_during_gpm_validation(
    cm_without_er_lp,
):
    # Positive Scenario: APM invoked successfully
    cm = cm_without_er_lp
    cm.adapter_factory = MagicMock()
    cm.gpm_source_path = (
        'car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators'
    )
    cm.gpm_file_path = (
        'instrument/ska_mid1/global_pointing_model_data/gpm-ska001-'
    )
    cm.handle_update_gpm_validation_result_callback = MagicMock()
    cb = cm.handle_update_gpm_validation_result_callback
    gpm_version_for_given_band = '1.5.1'
    band_found = 'Band_5a'
    cm.logger = MagicMock()
    gpm_validator = GPMValidator(cm, cm.logger)
    with patch(
        "ska_tmc_dishleafnode.manager.gpm_validator.ApplyPointingModel"
    ) as mock_apm_cls:
        mock_apm_instance = MagicMock()
        mock_apm_instance.do.return_value = (int(ResultCode.OK), "")
        mock_apm_cls.return_value = mock_apm_instance
        gpm_validator.invoke_apm_on_dish(
            gpm_version_for_given_band, band_found
        )
        cb.assert_called_once_with("Band_5a", "OK")
        assert cm.logger.debug.call_count >= 1


def test_to_check_apm_command_failed_during_gpm_validation(cm_without_er_lp):
    # Negative Scenario: APM Failed
    cm = cm_without_er_lp
    cm.gpm_source_path = (
        'car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators'
    )
    cm.gpm_file_path = (
        'instrument/ska_mid1/global_pointing_model_data/gpm-ska001-'
    )
    cm.handle_update_gpm_validation_result_callback = MagicMock()
    cb = cm.handle_update_gpm_validation_result_callback
    gpm_version_for_given_band = '1.5.1'
    band_found = 'Band_5a'
    cm.logger = MagicMock()
    gpm_validator = GPMValidator(cm, cm.logger)
    with patch(
        "ska_tmc_dishleafnode.manager.gpm_validator.ApplyPointingModel"
    ) as mock_apm_cls:
        mock_apm_instance = MagicMock()
        mock_apm_instance.do.return_value = (int(ResultCode.FAILED), "")
        mock_apm_cls.return_value = mock_apm_instance
        gpm_validator.invoke_apm_on_dish(
            gpm_version_for_given_band, band_found
        )
        cb.assert_called_once_with("Band_5a", "FAILED")
        assert cm.logger.error.call_count >= 1


def test_to_check_apm_command_exception_during_gpm_validation(
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    cm.logger = MagicMock()
    cm.gpm_source_path = (
        'car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators'
    )
    cm.gpm_file_path = Exception()
    gpm_version_for_given_band = '1.5.1'
    band_found = 'Band_5a'
    cm.handle_update_gpm_validation_result_callback = MagicMock()
    cb = cm.handle_update_gpm_validation_result_callback
    gpm_validator = GPMValidator(cm, cm.logger)
    with patch(
        "ska_tmc_dishleafnode.manager.gpm_validator.ApplyPointingModel"
    ) as mock_apm_cls:
        mock_apm_instance = MagicMock()
        mock_apm_instance.do.return_value = (ResultCode.FAILED, "")
        mock_apm_cls.return_value = mock_apm_instance
        gpm_validator.invoke_apm_on_dish(
            gpm_version_for_given_band, band_found
        )

        cb.assert_called_once_with("Band_5a", "FAILED")
        cm.logger.exception.assert_called_once()


def test_to_check_validate_gpm_version_with_error(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.logger = MagicMock()
    cm.gpm_source_path = (
        'car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators'
    )
    cm.gpm_file_path = (
        'instrument/ska_mid1/global_pointing_model_data/gpm-ska001-'
    )
    gpm_version_for_given_band = '1.5.1'
    band_found = 'Band_5a'
    cm.handle_update_gpm_validation_result_callback = MagicMock()
    cb = cm.handle_update_gpm_validation_result_callback
    gpm_validator = GPMValidator(cm, cm.logger)
    with patch(
        "ska_tmc_dishleafnode.manager.component_manager.ApplyPointingModel"
    ) as mock_apm_cls:
        mock_apm_instance = MagicMock()
        mock_apm_instance.get_global_pointing_data_json.return_value = (
            "{'random': 'value'}",
            "error",
        )
        mock_apm_cls.return_value = mock_apm_instance
        gpm_validator.validate_gpm_version(
            np.array(dish_param), gpm_version_for_given_band, band_found
        )
        cb.assert_called_once_with("Band_5a", "FAILED")
        cm.logger.error.assert_called_once()


def test_to_check_validate_gpm_version_with_success(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.logger = MagicMock()
    cm.gpm_source_path = (
        'car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators'
    )
    cm.gpm_file_path = (
        'instrument/ska_mid1/global_pointing_model_data/gpm-ska001-'
    )
    gpm_version_for_given_band = '1.5.1'
    band_found = 'Band_1'
    cm.handle_update_gpm_validation_result_callback = MagicMock()
    gpm_validator = GPMValidator(cm, cm.logger)
    gpm_validator.validate_gpm_version(
        np.array(dish_param), gpm_version_for_given_band, band_found
    )
    cm.handle_update_gpm_validation_result_callback.assert_called_once_with(
        "Band_1", "OK"
    )
    assert cm.logger.debug.call_count >= 1


def test_to_check_validate_gpm_version_with_mismatch(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.logger = MagicMock()
    cm.gpm_source_path = (
        'car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators'
    )
    cm.gpm_file_path = (
        'instrument/ska_mid1/global_pointing_model_data/gpm-ska001-'
    )
    gpm_version_for_given_band = '1.5.1'
    band_found = 'Band_5a'
    cm.handle_update_gpm_validation_result_callback = MagicMock()
    gpm_validator = GPMValidator(cm, cm.logger)
    gpm_validator.validate_gpm_version(
        np.array(dish_param), gpm_version_for_given_band, band_found
    )
    cm.handle_update_gpm_validation_result_callback.assert_called_once_with(
        "Band_5a", "FAILED"
    )
    assert cm.logger.debug.call_count >= 1


def test_to_check_validate_gpm_version_with_exception(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.logger = MagicMock()
    cm.gpm_source_path = (
        'car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators'
    )
    cm.gpm_file_path = Exception()
    gpm_version_for_given_band = '1.5.1'
    band_found = 'Band_5a'
    cm.handle_update_gpm_validation_result_callback = MagicMock()
    gpm_validator = GPMValidator(cm, cm.logger)
    gpm_validator.validate_gpm_version(
        np.array(dish_param), gpm_version_for_given_band, band_found
    )
    cm.handle_update_gpm_validation_result_callback.assert_called_once_with(
        "Band_5a", "FAILED"
    )
    assert cm.logger.exception.call_count >= 1


def test_to_check_get_band_info_success(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.logger = MagicMock()
    band_5b_version = '1.5.1'
    set_band = 'Band_5b'
    band_name = "band5bpointingmodelparams"
    cm.gpm_version[set_band] = band_5b_version
    gpm_validator = GPMValidator(cm, cm.logger)
    version, band = gpm_validator.get_band_info(band_name)
    assert version == band_5b_version
    assert band == set_band
    cm.logger.info.assert_called_once()
    cm.logger.debug.assert_called_once()


def test_to_check_get_band_info_failure(cm_without_er_lp):
    cm = cm_without_er_lp
    # Scenario : Exception occurred
    cm.logger = MagicMock()
    band_name = Exception()
    gpm_validator = GPMValidator(cm, cm.logger)
    version, band = gpm_validator.get_band_info(band_name)
    assert not version
    assert not band
    cm.logger.exception.assert_called_once()


def test_handler_puts_event_in_queue(cm):
    cm.event_queues = MagicMock()
    event_receiver = DishLNEventReceiver(cm, cm.logger)
    queue_key = "band2pointingmodelparams"
    mock_event_data = MagicMock(spec=tango.EventData)
    handler = event_receiver._create_pointing_model_handler(queue_key)
    handler(mock_event_data)
    cm.event_queues.__getitem__.assert_called_once_with(queue_key)
    cm.event_queues[queue_key].put.assert_called_once_with(mock_event_data)


def test_update_dish_pointing_model_param_calls(
    cm_without_er_lp,
):
    # Scenario: Validate GPM version called once from
    # update_dish_pointing_model_param
    cm = cm_without_er_lp
    logger = MagicMock()
    cm._update_dish_pointing_model_param = MagicMock()
    cm.evaluate_and_update_health_state = MagicMock()
    gpm_validator = GPMValidator(cm, logger)
    gpm_validator.get_band_info = MagicMock(return_value=("1.5.1", "Band_1"))
    gpm_validator.validate_gpm_version = MagicMock(return_value=None)
    gpm_validator.update_dish_params_and_validate_gpm(
        np.array(dish_param),
        band_name="band1pointingmodelparams",
    )
    gpm_validator.get_band_info.assert_called_once_with(
        "band1pointingmodelparams"
    )
    args, _ = gpm_validator.validate_gpm_version.call_args
    np.testing.assert_array_equal(args[0], dish_param)
    assert args[1] == "1.5.1"
    assert args[2] == "Band_1"
    logger.info.assert_called_once()
    logger.debug.assert_called_once()
    cm._update_dish_pointing_model_param.assert_called_once()
    cm.evaluate_and_update_health_state.assert_called_once()

    # Scenario 2: GPM version unknown
    cm.handle_update_gpm_validation_result_callback = MagicMock()
    logger = MagicMock()
    gpm_validator.get_band_info = MagicMock(return_value=("UNKNOWN", "Band_1"))
    gpm_validator.update_dish_params_and_validate_gpm(
        np.array(dish_param),
        band_name="band1pointingmodelparams",
    )
    logger.error.call_count >= 1
    cm.handle_update_gpm_validation_result_callback.assert_called_once_with(
        "Band_1", "FAILED"
    )

    # Scenario 3: invoke gpm gets called once
    gpm_validator.get_band_info = MagicMock(return_value=("1.5.2", "Band_1"))
    gpm_validator.invoke_apm_on_dish = MagicMock(return_value=None)
    gpm_validator.update_dish_params_and_validate_gpm(
        np.array([]),
        band_name="band1pointingmodelparams",
    )
    gpm_validator.invoke_apm_on_dish.assert_called_once_with("1.5.2", "Band_1")

    # Scenario 4: Invalid band name
    logger = MagicMock()
    gpm_validator = GPMValidator(cm, logger)
    gpm_validator.update_dish_params_and_validate_gpm(
        np.array(dish_param),
        band_name="band10pointingmodelparams",
    )
    logger.error.assert_called_once()

    # Scenario 5: update method gets called once from CM
    cm.initialization_complete.set()
    cm.gpm_validator.update_dish_params_and_validate_gpm = MagicMock()
    cm.update_dish_pointing_model_param(dish_param, "band1pointingmodelparams")
    cm.gpm_validator.update_dish_params_and_validate_gpm.assert_called_once()
