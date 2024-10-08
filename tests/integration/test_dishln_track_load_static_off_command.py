"""Integration test for Track and TrackStop command
"""
import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import FaultType, PointingState

from tests.settings import (
    COMMAND_COMPLETED,
    COMMAND_FAILED,
    COMMAND_TIMEOUT,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    logger,
)

argin = json.dumps([0.1, 0.2])


def track_load_static_off_dish_leaf_node_timeout(
    tango_context,
    dishln_name,
    group_callback,
    input_str,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectPointingState(PointingState.READY)

    POINTINGSTATE_ID = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=2,
    )
    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    TIMEOUT_DEFECT = json.dumps(
        {
            "enabled": True,
            "fault_type": FaultType.STUCK_IN_INTERMEDIATE_STATE,
            "error_message": "Device stuck in intermediate state",
            "result": ResultCode.FAILED,
            "intermediate_state": PointingState.READY,
        }
    )

    # Set defect on DishMaster
    dish_master.SetDefective(TIMEOUT_DEFECT)

    result_config, unique_id_config = dish_leaf_node.TrackLoadStaticOff(argin)
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    # Wait for the command timeout to be occurred. The command timeout is set
    # to 15 sec.
    time.sleep(18)

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_TIMEOUT),
        lookahead=8,
    )

    RESET_DEFECT = json.dumps(
        {
            "enabled": False,
            "fault_type": FaultType.STUCK_IN_INTERMEDIATE_STATE,
            "error_message": "Device stuck in intermediate state",
            "result": ResultCode.FAILED,
            "intermediate_state": PointingState.READY,
        }
    )
    dish_master.SetDefective(RESET_DEFECT)

    dish_leaf_node.unsubscribe_event(POINTINGSTATE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_track_load_static_off_command_timeout(
    tango_context, group_callback, json_factory
):
    track_load_static_off_dish_leaf_node_timeout(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        argin,
    )


def track_load_static_off_dish_leaf_node_error_propagation(
    tango_context,
    dishln_name,
    group_callback,
    input_str,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectPointingState(PointingState.READY)

    POINTINGSTATE_ID = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=2,
    )
    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    ERROR_PROPAGATION_DEFECT = json.dumps(
        {
            "enabled": True,
            "fault_type": FaultType.LONG_RUNNING_EXCEPTION,
            "error_message": "Exception occured, command failed.",
            "result": ResultCode.FAILED,
        }
    )

    # Set defect on DishMaster
    dish_master.SetDefective(ERROR_PROPAGATION_DEFECT)

    result_config, unique_id_config = dish_leaf_node.TrackLoadStaticOff(argin)
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_FAILED),
        lookahead=8,
    )

    RESET_DEFECT = json.dumps(
        {
            "enabled": False,
            "fault_type": FaultType.FAILED_RESULT,
            "error_message": "Default exception.",
            "result": ResultCode.FAILED,
        }
    )
    dish_master.SetDefective(RESET_DEFECT)

    dish_leaf_node.unsubscribe_event(POINTINGSTATE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_track_load_static_off_command_error_propagation(
    tango_context, group_callback, json_factory
):
    track_load_static_off_dish_leaf_node_error_propagation(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        argin,
    )


def track_load_static_off_dish_leaf_node(
    tango_context,
    dishln_name,
    group_callback,
    input_str,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectPointingState(PointingState.READY)

    POINTINGSTATE_ID = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=2,
    )
    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    result_config, unique_id_config = dish_leaf_node.TrackLoadStaticOff(argin)
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    dish_leaf_node.unsubscribe_event(POINTINGSTATE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_track_load_static_off_command(
    tango_context, group_callback, json_factory
):
    track_load_static_off_dish_leaf_node(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        argin,
    )
