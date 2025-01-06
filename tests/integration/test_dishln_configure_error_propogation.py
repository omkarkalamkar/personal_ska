import json
import logging
from time import sleep

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory, DishMode, FaultType, PointingState

from tests.settings import (
    COMMAND_COMPLETED,
    COMMAND_CONFIGURE_BAND_TIMEOUT,
    COMMAND_FAILED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    DISHLN_POINTING_DEVICE,
    build_partial_configure_data,
    tear_down,
)

OFFSET = 5.0


def partial_configure_dish_leaf_node_error_propagation(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
    partial_configure_input_str,
):
    """Partial configure flow for dish leaf node."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dishln_pointing_device = dev_factory.get_device(DISHLN_POINTING_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    sleep(1)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    logging.info("dishmode_event_id: %s", dishmode_event_id)
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )
    logging.info("pointingstate_event_id: %s", pointingstate_event_id)
    source_offset_event_id = dish_leaf_node.subscribe_event(
        "sourceOffset",
        tango.EventType.CHANGE_EVENT,
        group_callback["sourceOffset"],
    )
    logging.info("source_offset_event_id: %s", source_offset_event_id)
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    logging.info("lrcr_event_id: %s", lrcr_event_id)
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )

    partial_configurations = build_partial_configure_data(
        partial_configure_input_str, OFFSET
    )

    input_str = partial_configurations[0]

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

    result_config, unique_id_config = dish_leaf_node.Configure(input_str)
    assert result_config[0] == ResultCode.QUEUED
    load_conf = json.loads(input_str)

    ca_offset = load_conf["pointing"]["target"]["ca_offset_arcsec"]
    ie_offset = load_conf["pointing"]["target"]["ie_offset_arcsec"]

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_FAILED),
        lookahead=8,
    )
    # Assert change event is occuring and values are reflecting
    # on sourceOffset attribute.
    group_callback["sourceOffset"].assert_change_event(
        [ca_offset, ie_offset],
        lookahead=2,
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
    dish_leaf_node.unsubscribe_event(source_offset_event_id)
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    tear_down(
        dish_leaf_node, dish_master, group_callback, dishln_pointing_device
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_partial_configure_error_propogation(
    tango_context, group_callback, json_factory
):
    """Test partial configure functionality on Dish Leaf Node."""
    partial_configure_dish_leaf_node_error_propagation(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
        json_factory("partial_configure"),
    )


def configure_dish_leaf_node_error_propagation(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
):
    """Partial configure flow for dish leaf node."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dishln_pointing_device = dev_factory.get_device(DISHLN_POINTING_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    sleep(1)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    logging.info("dishmode_event_id: %s", dishmode_event_id)
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )
    logging.info("pointingstate_event_id: %s", pointingstate_event_id)
    source_offset_event_id = dish_leaf_node.subscribe_event(
        "sourceOffset",
        tango.EventType.CHANGE_EVENT,
        group_callback["sourceOffset"],
    )
    logging.info("source_offset_event_id: %s", source_offset_event_id)
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    logging.info("lrcr_event_id: %s", lrcr_event_id)
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
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

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED

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
    dish_leaf_node.unsubscribe_event(source_offset_event_id)
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    tear_down(
        dish_leaf_node, dish_master, group_callback, dishln_pointing_device
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_configure_error_propagation(
    tango_context, group_callback, json_factory
):
    """Test configure error propogation functionality on Dish Leaf Node."""
    configure_dish_leaf_node_error_propagation(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
    )


def configure_dish_leaf_node_timeout(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
):
    """Partial configure flow for dish leaf node."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dishln_pointing_device = dev_factory.get_device(DISHLN_POINTING_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    sleep(1)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    logging.info("dishmode_event_id: %s", dishmode_event_id)
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )
    logging.info("pointingstate_event_id: %s", pointingstate_event_id)
    source_offset_event_id = dish_leaf_node.subscribe_event(
        "sourceOffset",
        tango.EventType.CHANGE_EVENT,
        group_callback["sourceOffset"],
    )
    logging.info("source_offset_event_id: %s", source_offset_event_id)
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    logging.info("lrcr_event_id: %s", lrcr_event_id)
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
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

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED
    # Wait for the command timeout to be occurred. The command timeout is set
    # to 15 sec.
    sleep(18)

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_CONFIGURE_BAND_TIMEOUT),
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
    dish_leaf_node.unsubscribe_event(source_offset_event_id)
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    tear_down(
        dish_leaf_node, dish_master, group_callback, dishln_pointing_device
    )


@pytest.mark.skip
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_configure_error_timeout(tango_context, group_callback, json_factory):
    """Test configure error propogation functionality on Dish Leaf Node."""
    configure_dish_leaf_node_timeout(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
    )
