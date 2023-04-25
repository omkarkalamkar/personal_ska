import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode

from tests.settings import DISH_LEAF_NODE_DEVICE, DISH_MASTER_DEVICE, event_remover, logger


def setstowmode_command(tango_context, dishln_name, group_callback):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_FP)
    dish_master.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=2,
    )
    event_remover(
        group_callback,
        ["longRunningCommandsInQueue", "longRunningCommandResult"],
    )
    dish_leaf_node.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandsInQueue"],
    )

    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
    )

    result, unique_id = dish_leaf_node.SetStandbyLPMode()
    assert result[0] == ResultCode.QUEUED
    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    result_stow, unique_id_stow = dish_leaf_node.SetStowMode()

    group_callback["longRunningCommandsInQueue"].assert_change_event(
        (
            "SetStandbyLPMode",
            "SetStowMode",
        ),
        lookahead=2,
    )
    logger.info(f"Command ID: {unique_id_stow} Returned result: {result_stow}")

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=2,
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_stow[0], str(int(ResultCode.OK))),
        lookahead=2,
    )

    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
        lookahead=3,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_setstowmode_command(tango_context, group_callback):
    setstowmode_command(tango_context, DISH_LEAF_NODE_DEVICE, group_callback)
