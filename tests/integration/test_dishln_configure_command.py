import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode, PointingState

from tests.settings import dish_leaf_node_device, event_remover, logger


def configure_dish_leaf_node(
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
    dish_master = dev_factory.get_device(dish_leaf_node_device)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dish_master.subscribe_event(
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

    result_op, unique_id_op = dish_leaf_node.SetOperateMode()
    assert result_op[0] == ResultCode.QUEUED
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        (
            "SetStandbyFPMode",
            "SetOperateMode",
        )
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
    dish_master.SetDirectPointingState(PointingState.READY)
    assert dish_master.PointingState == PointingState.READY
    dish_master.subscribe_event(
        "PointingState.READY",
        tango.EventType.CHANGE_EVENT,
        group_callback["PointingState.READY"],
    )
    group_callback["PointingState.READY"].assert_change_event(
        (PointingState.READY),
        lookahead=2,
    )

    result_op, unique_id_op = dish_leaf_node.Configure(configure_input_str)
    assert result_op[0] == ResultCode.QUEUED
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        ("SetStandbyFPMode", "SetOperateMode", "Configure")
    )
    logger.info(f"Command ID: {unique_id_op} Returned result: {result_op}")

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_op[0], str(int(ResultCode.OK))),
        lookahead=2,
    )
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
        lookahead=2,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_configure_command(tango_context, group_callback, json_factory):
    configure_dish_leaf_node(
        tango_context,
        dish_leaf_node_device,
        group_callback,
        json_factory("dishleafnode_configure"),
    )
