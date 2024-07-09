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


def setstandbylpmode_command(tango_context, dishln_name, group_callback):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    DISHMODE_ID = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    assert result_fp == ResultCode.QUEUED
    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=2,
    )

    result_lp, unique_id_lp = dish_leaf_node.SetStandbyLPMode()
    assert result_lp[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_lp[0], COMMAND_COMPLETED),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=5,
    )
    dish_leaf_node.unsubscribe_event(DISHMODE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_setstandbylpmode_command(tango_context, group_callback):
    setstandbylpmode_command(
        tango_context, DISH_LEAF_NODE_DEVICE, group_callback
    )
