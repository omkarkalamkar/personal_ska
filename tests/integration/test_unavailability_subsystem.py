import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode

from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    logger,
)


def device_unavailability(tango_context, dishln_name, group_callback):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)

    availablity_value = dish_leaf_node.read_attribute(
        "isSubsystemAvailable"
    ).value
    assert availablity_value

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
        (
            unique_id_fp[0],
            COMMAND_COMPLETED,
        ),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=2,
    )

    result_op, unique_id_op = dish_leaf_node.SetOperateMode()
    assert result_op[0] == ResultCode.QUEUED
    logger.info(f"Command ID: {unique_id_op} Returned result: {result_op}")

    group_callback["longRunningCommandResult"].assert_change_event(
        (
            unique_id_op[0],
            COMMAND_COMPLETED,
        ),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_device_unavailability(tango_context, group_callback):
    device_unavailability(tango_context, DISH_LEAF_NODE_DEVICE, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_dish_leafnode_command_timeout_low(tango_context):
    """Test Dish Leaf Node command timeout for Low."""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    dish_leafnode_low = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)

    dish_leafnode_low.commandTimeOut = 200
    assert dish_leafnode_low.commandTimeOut == 200
