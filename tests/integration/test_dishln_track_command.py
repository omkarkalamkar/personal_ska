"""Integration test for Track and TrackStop command
"""
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode, PointingState

from tests.settings import DISH_LEAF_NODE_DEVICE, DISH_MASTER_DEVICE, event_remover, logger


def track_dish_leaf_node(
    tango_context,
    dishln_name,
    group_callback,
    track_input_str,
):

    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    event_remover(
        group_callback,
        ["longRunningCommandsInQueue", "longRunningCommandResult"],
    )
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.OPERATE)
    dish_master.SetDirectPointingState(PointingState.READY)
    dish_master.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=2,
    )

    dish_master.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    dish_leaf_node.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandsInQueue"],
    )
    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
    )

    result_config, unique_id_config = dish_leaf_node.Track(track_input_str)
    assert result_config[0] == ResultCode.QUEUED
    group_callback["longRunningCommandsInQueue"].assert_change_event(("Track",))
    logger.info(f"Command ID: {unique_id_config} Returned result: {result_config}")

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], str(int(ResultCode.OK))),
        lookahead=6,
    )

    time.sleep(3)
    result_config, unique_id_config = dish_leaf_node.TrackStop()

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], str(int(ResultCode.OK))),
        lookahead=6,
    )
    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=2,
    )
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
        lookahead=6,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_track_command(tango_context, group_callback, json_factory):
    track_dish_leaf_node(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_track"),
    )
