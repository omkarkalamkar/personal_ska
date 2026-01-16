import json
import time
from unittest import mock

import pytest
import tango
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory
from ska_tmc_common.enum import DishMode, PointingState

from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from ska_tmc_dishleafnode.manager.event_manager import DishLNEventManager
from tests.settings import (
    COMMAND_COMPLETED,
    DISH_MASTER_DEVICE,
    SDP_QUEUE_CONNECTOR_DEVICE,
    logger,
    simulate_dish_mode_event,
    simulate_result_code_event,
    wait_for_dish_mode,
)

POINTING_CAL1 = [1.1, 2.2, 3.3]


def test_trackloadstaticoff_command(
    tango_context, cm_without_er_lp, task_callback, group_callback
):
    """Test the successful completion of the TrackLoadStaticOff command."""
    cm = cm_without_er_lp
    dish_device = DevFactory().get_device(DISH_MASTER_DEVICE)
    cm.get_device(cm.dish_dev_name)._unresponsive = False
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
        (Anything, '[0, "Command Completed"]'),
        lookahead=10,
    )[
        "attribute_value"
    ]

    assert "TrackLoadStaticOff" in unique_id
    assert "Command Completed" in message
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
    cm_without_er_lp, argin, task_callback
):
    """Test the failure scenario while invoking
    TrackLoadStaticOff command."""
    cm = cm_without_er_lp
    cm.get_device(cm.dish_dev_name)._unresponsive = False
    assert cm.is_trackloadstaticoff_allowed()

    status, message = cm.track_load_static_off(
        argin, task_callback=task_callback
    )
    assert status == TaskStatus.REJECTED
    assert (
        "Input argument is incorrect for TrackLoadStaticOff command."
        == message
    )


def test_configure_command_completed_with_correction_key_reset(
    cm_without_er_lp,
    task_callback,
    json_factory,
):
    """Test Configure command with correction key as RESET"""
    cm = cm_without_er_lp
    cm.kvalue_validation_thread.cancel()
    set_kvalue_command = SetKValue(cm, logger=logger)
    attrs = {
        'SetKValue.return_value': ([ResultCode.OK], ["Command Completed"]),
        'TrackLoadStaticOff.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
        'ConfigureBand2.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
        "GenerateProgramTrackTable.return_value": (ResultCode.STARTED, ""),
    }
    dishMock = mock.Mock(
        programTrackTable=[
            775853423.2247269,
            178.758613204265,
            31.165682681453,
        ],
        **attrs,
    )
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    set_kvalue_command._adapter_factory = adapter_factory
    cm.adapter_factory = adapter_factory

    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    configure_input_str = json.loads(configure_input_str)
    configure_input_str["pointing"]["correction"] = "RESET"
    configure_input_str = json.dumps(configure_input_str)
    cm.configure(configure_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    cm.update_device_pointing_state(PointingState.TRACK)
    cm.update_device_configured_band("2")
    time.sleep(2)
    simulate_dish_mode_event(cm, DishMode.OPERATE)
    simulate_result_code_event(cm, "Track", ResultCode.OK)
    simulate_result_code_event(cm, "TrackLoadStaticOff", ResultCode.OK)
    simulate_result_code_event(cm, "ConfigureBand2", ResultCode.OK)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=2,
    )

    dishMock.TrackLoadStaticOff.assert_called_once_with([0.0, 0.0])


def test_configure_command_completed_with_correction_key_update(
    tango_context,
    cm,
    group_callback,
):
    """Test configure command with correction key as UPDATE"""
    cm.get_device(cm.dish_dev_name).update_unresponsive(False, "")
    dish_device = DevFactory().get_device(DISH_MASTER_DEVICE)
    dish_device.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
        stateless=True,
    )
    cm.correction_key = "UPDATE"
    # Code to check new pointing offsets are applied when key is UPDATE
    # and configure is partial config
    cm.dish_id = "SKA001"
    SDP_QUEUE_CONNECTOR_FQDN = (
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/" "pointing_cal_{dish_id}"
    )
    sdp_queue_connector = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)

    cm.event_manager = True
    cm.event_manager_object = DishLNEventManager(cm, logger=cm.logger)

    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN)
    sdp_queue_connector.SetPointingCalSka001(POINTING_CAL1)
    unique_id = ""
    count = 0
    while "TrackLoadStaticOff" not in unique_id and count < 10:
        unique_id, _ = group_callback[
            "longRunningCommandResult"
        ].assert_change_event(
            (Anything, '[0, "Command Completed"]'),
            lookahead=10,
        )[
            "attribute_value"
        ]
        count = count + 1
        time.sleep(1)


def test_correction_key_reset_partial_config(
    tango_context,
    cm_without_er_lp,
    group_callback,
    task_callback,
    json_factory,
):
    """Test correction key RESET functionality for partial config"""
    cm = cm_without_er_lp
    dish_device = DevFactory().get_device(DISH_MASTER_DEVICE)
    set_kvalue_command = SetKValue(cm, logger=logger)
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK
    dish_device.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
        stateless=True,
    )
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    cm.update_device_dish_mode(DishMode.OPERATE)
    wait_for_dish_mode(cm, DishMode.OPERATE)
    assert cm.is_configure_allowed()
    primary_configure_input_str = json_factory("dishleafnode_configure")
    cm.primary_configuration = json.loads(primary_configure_input_str)
    cm.update_device_configured_band("2")
    cm.update_device_pointing_state(PointingState.TRACK)

    configure_input_str = json_factory("partial_configure")
    configure_input_str = json.loads(configure_input_str)
    configure_input_str["pointing"]["correction"] = "RESET"
    configure_input_str = json.dumps(configure_input_str)
    cm.configure(configure_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    time.sleep(5)
    simulate_result_code_event(cm, "TrackLoadStaticOff", ResultCode.OK)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )


def test_correction_key_update_partial_config(
    tango_context,
    cm_without_er_lp,
    group_callback,
    task_callback,
    json_factory,
):
    """Test correction UPDATE key functionality for partial config"""

    cm = cm_without_er_lp
    dish_device = DevFactory().get_device(DISH_MASTER_DEVICE)
    set_kvalue_command = SetKValue(cm, logger=logger)
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK
    dish_device.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
        stateless=True,
    )
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("partial_configure")
    configure_input_str = json.loads(configure_input_str)
    configure_input_str["pointing"]["correction"] = "UPDATE"
    configure_input_str = json.dumps(configure_input_str)
    cm.configure(configure_input_str, task_callback=task_callback)
    # Code to check new pointing offsets are applied when key is UPDATE
    # and configure is partial config
    SDP_QUEUE_CONNECTOR_FQDN = (
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/" "pointing_cal_{dish_id}"
    )
    sdp_queue_connector = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    cm.dish_id = "SKA001"
    cm.event_manager = True
    cm.event_manager_object = DishLNEventManager(cm, logger=cm.logger)

    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN)
    dish_device = DevFactory().get_device(DISH_MASTER_DEVICE)
    sdp_queue_connector.SetPointingCalSka001(POINTING_CAL1)

    unique_id = ""
    message = ""
    count = 0
    while "TrackLoadStaticOff" not in unique_id and count < 10:
        unique_id, message = group_callback[
            "longRunningCommandResult"
        ].assert_change_event(
            (Anything, '[0, "Command Completed"]'),
            lookahead=10,
        )[
            "attribute_value"
        ]
        count = count + 1
        time.sleep(1)
    assert "Command Completed" in message


@pytest.mark.parametrize("correction_key", ["", "MAINTAIN"])
def test_correction_key_maintain_empty_partial_main_config(
    tango_context,
    cm_without_er_lp,
    group_callback,
    correction_key,
):
    """Test correction MAINTAIN key functionality for main config"""
    cm = cm_without_er_lp
    dish_device = DevFactory().get_device(DISH_MASTER_DEVICE)
    set_kvalue_command = SetKValue(cm, logger=logger)
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK
    dish_device.SetDirectDishMode(DishMode.STANDBY_FP)
    time.sleep(0.2)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    cm.correction_key = correction_key
    # Code to check new pointing offsets are not applied when key
    # is MAINTAIN and configure is partial config
    SDP_QUEUE_CONNECTOR_FQDN = (
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/" "pointing_cal_{dish_id}"
    )
    sdp_queue_connector = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    cm.dish_id = "SKA001"
    cm.event_manager = True
    cm.event_manager_object = DishLNEventManager(cm, logger=cm.logger)

    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN)

    with pytest.raises(AssertionError):
        sdp_queue_connector.SetPointingCalSka001(POINTING_CAL1)
        unique_id, _ = group_callback[
            "longRunningCommandResult"
        ].assert_change_event(
            (Anything, COMMAND_COMPLETED),
            lookahead=10,
        )[
            "attribute_value"
        ]
        assert "TrackLoadStaticOff" in unique_id
