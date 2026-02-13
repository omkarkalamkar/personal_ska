import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import Band, DishMode, FaultType, PointingState

from tests.settings import (
    COMMAND_COMPLETED,
    COMMAND_FAILED,
    COMMAND_TIMEOUT,
    DISH_CONFIGURE_1_0,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    logger,
    tear_down,
)


def configureband_command(tango_context, dishln_name, group_callback, argin):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )
    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=7,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    assert result_fp[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=7,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=7,
    )

    result_op, unique_id_op = dish_leaf_node.ConfigureBand(argin)
    assert result_op[0] == ResultCode.QUEUED
    logger.info(f"Command ID: {unique_id_op} Returned result: {result_op}")

    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=7,
    )
    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=6,
    )
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_op[0], COMMAND_COMPLETED),
        lookahead=7,
    )
    argin_reciever_band = (
        json.loads(argin).get("dish", {}).get("receiver_band", "")
    )
    if argin_reciever_band == "5a":
        argin_reciever_band = "5"
    elif argin_reciever_band == "5b":
        argin_reciever_band = "6"
    assert dish_master.configuredBand == Band(int(argin_reciever_band))

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)

    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.test_configureband
@pytest.mark.parametrize(
    "argin",
    ["1", "2", "3", "4", "5a", "5b", DISH_CONFIGURE_1_0],
)
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_configureband_command(tango_context, group_callback, argin):
    if argin != DISH_CONFIGURE_1_0:
        argin = json.dumps({"dish": {"receiver_band": str(argin)}})
    configureband_command(
        tango_context, DISH_LEAF_NODE_DEVICE, group_callback, argin
    )


def configureband_command_error_propogation(
    tango_context, dishln_name, group_callback
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=2,
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
    argin = json.dumps({"dish": {"receiver_band": "1"}})
    result_op, unique_id_op = dish_leaf_node.ConfigureBand(argin)
    assert result_op[0] == ResultCode.QUEUED
    logger.info(f"Command ID: {unique_id_op} Returned result: {result_op}")

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_op[0], COMMAND_FAILED),
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

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)

    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_configureband_command_error_propogation(
    tango_context, group_callback
):
    configureband_command_error_propogation(
        tango_context, DISH_LEAF_NODE_DEVICE, group_callback
    )


def configureband_command_timeout(tango_context, dishln_name, group_callback):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=2,
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
    argin = json.dumps({"dish": {"receiver_band": "1"}})
    result_op, unique_id_op = dish_leaf_node.ConfigureBand(argin)
    assert result_op[0] == ResultCode.QUEUED
    logger.info(f"Command ID: {unique_id_op} Returned result: {result_op}")

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_op[0], COMMAND_TIMEOUT),
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

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)

    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_configureband_command_timeout(tango_context, group_callback):
    configureband_command_timeout(
        tango_context, DISH_LEAF_NODE_DEVICE, group_callback
    )
