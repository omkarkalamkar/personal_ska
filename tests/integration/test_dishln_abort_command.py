import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode, FaultType, PointingState

from tests.settings import (
    COMMAND_COMPLETED,
    COMMAND_FAILED,
    COMMAND_TIMEOUT,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    logger,
    tear_down,
    wait_and_validate_attribute_value_available,
)


def abort_on_dish_leaf_node(
    tango_context,
    group_callback,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    result_code, unique_id = dish_leaf_node.Abort()
    assert result_code[0] == ResultCode.STARTED
    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    dish_mode_event = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], COMMAND_COMPLETED),
        lookahead=7,
    )
    group_callback["dishMode"].assert_change_event(
        DishMode.STANDBY_FP,
        lookahead=7,
    )
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    dish_leaf_node.unsubscribe_event(dish_mode_event)


def abort_when_configured(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
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
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )

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

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    group_callback["pointingState"].assert_change_event(
        (PointingState.SLEW),
        lookahead=6,
    )
    wait_and_validate_attribute_value_available(
        dish_leaf_node, "pointingState", PointingState.TRACK, timeout=30
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    result_abort, unique_id_abort = dish_leaf_node.Abort()
    logger.info(
        f"Command ID: {unique_id_abort} Returned result: {result_abort}"
    )

    assert result_abort == ResultCode.STARTED

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_abort[0], COMMAND_COMPLETED),
        lookahead=7,
    )
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)


def abort_while_configuring(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
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
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )

    assert result_fp[0] == ResultCode.QUEUED
    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=5,
    )

    assert dish_leaf_node.pointingState == PointingState.READY

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )

    result_abort, unique_id_abort = dish_leaf_node.Abort()
    logger.info(
        f"Command ID: {unique_id_abort} Returned result: {result_abort}"
    )

    assert result_abort == ResultCode.STARTED

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_abort[0], COMMAND_COMPLETED),
        lookahead=5,
    )

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)

    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_abort_command(tango_context, group_callback):
    abort_on_dish_leaf_node(
        tango_context,
        group_callback,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_abort_after_configure(tango_context, group_callback, json_factory):
    abort_when_configured(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_abort_while_configuring(tango_context, group_callback, json_factory):
    abort_while_configuring(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_abort_timeout(tango_context, group_callback):
    abort_timeout(tango_context, DISH_LEAF_NODE_DEVICE, group_callback)


def abort_timeout(
    tango_context,
    dishln_name,
    group_callback,
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

    result, unique_id = dish_leaf_node.SetStandbyFPMode()

    logger.debug("Command id: %s | Returned result: %s", unique_id, result)
    assert result[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], COMMAND_COMPLETED),
        lookahead=2,
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=5,
    )

    dish_master.SetDelayInfo(json.dumps({"Abort": 35}))
    result, unique_id = dish_leaf_node.Abort()

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], COMMAND_TIMEOUT),
        lookahead=3,
    )
    dish_leaf_node.unsubscribe_event(lrcr_event_id)

    lrcr_event_id = dish_master.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    wait_and_validate_attribute_value_available(
        dish_master, "dishMode", DishMode.STANDBY_FP
    )

    wait_and_validate_attribute_value_available(
        dish_master, "pointingState", PointingState.READY
    )

    # dish master ABORT LRCR OK is asserted
    group_callback["longRunningCommandResult"].assert_change_event(
        (Anything, COMMAND_COMPLETED),
        lookahead=3,
    )

    dish_master.ResetDelayInfo()
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_master.unsubscribe_event(lrcr_event_id)
    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_abort_exception(tango_context, group_callback):
    abort_exception(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
    )


def abort_exception(tango_context, dishln_name, group_callback):
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

    result, unique_id = dish_leaf_node.SetStandbyFPMode()

    logger.debug("Command id: %s | Returned result: %s", unique_id, result)
    assert result[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], COMMAND_COMPLETED),
        lookahead=2,
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=5,
    )

    ERROR_PROPAGATION_DEFECT = json.dumps(
        {
            "enabled": True,
            "fault_type": FaultType.LONG_RUNNING_EXCEPTION,
            "error_message": "Exception occured, command failed.",
            "result": ResultCode.FAILED,
        }
    )

    dish_master.SetDefective(ERROR_PROPAGATION_DEFECT)
    _, unique_id = dish_leaf_node.Abort()

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], COMMAND_FAILED),
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
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    tear_down(dish_leaf_node, dish_master, group_callback)
