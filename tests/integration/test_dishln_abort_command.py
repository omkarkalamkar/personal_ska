import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode, PointingState

from tests.settings import DISH_LEAF_NODE_DEVICE, DISH_MASTER_DEVICE, event_remover, logger


def abort_on_dish_leaf_node(
    tango_context,
    group_callback,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    event_remover(
        group_callback,
        ["longRunningCommandsInQueue", "longRunningCommandResult"],
    )
    result_fp, _ = dish_leaf_node.AbortCommands()
    assert result_fp[0] == ResultCode.OK


def abort_when_configured(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    event_remover(
        group_callback,
        ["longRunningCommandsInQueue", "longRunningCommandResult"],
    )
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dish_master.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    dish_master.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    dish_leaf_node.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandsInQueue"],
    )

    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    assert result_fp[0] == ResultCode.QUEUED
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        ("SetStandbyFPMode",),
    )
    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], str(int(ResultCode.OK))),
        lookahead=2,
    )

    result_config, unique_id_config = dish_leaf_node.Configure(configure_input_str)
    assert result_config[0] == ResultCode.QUEUED
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        ("SetStandbyFPMode", "Configure")
    )
    logger.info(f"Command ID: {unique_id_config} Returned result: {result_config}")

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], str(int(ResultCode.OK))),
        lookahead=6,
    )

    result_abort, unique_id_abort = dish_leaf_node.AbortCommands()
    logger.info(f"Command ID: {unique_id_abort} Returned result: {result_abort}")

    assert result_abort == ResultCode.OK

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=6,
    )


@pytest.mark.post_deployment
def test_abort_command(tango_context, group_callback):
    abort_on_dish_leaf_node(
        tango_context,
        group_callback,
    )


@pytest.mark.post_deployment
def test_abort_when_configure(tango_context, group_callback, json_factory):
    abort_when_configured(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
    )
