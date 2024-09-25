"""Integration test for Track and TrackStop command
"""
import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import PointingState

from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    logger,
)

argin = json.dumps([0.1, 0.2])


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
    # dish_master.SetDirectDishMode(DishMode.OPERATE)
    dish_master.SetDirectPointingState(PointingState.READY)
    # DISHMODE_ID = dish_leaf_node.subscribe_event(
    #     "dishMode",
    #     tango.EventType.CHANGE_EVENT,
    #     group_callback["dishMode"],
    # )
    POINTINGSTATE_ID = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )
    # group_callback["dishMode"].assert_change_event(
    #     (DishMode.OPERATE),
    #     lookahead=2,
    # )
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

    # group_callback["pointingState"].assert_change_event(
    #     (PointingState.TRACK),
    #     lookahead=5,
    # )
    # group_callback["dishMode"].assert_change_event(
    #     (DishMode.OPERATE),
    #     lookahead=5,
    # )
    time.sleep(3)
    # result_config, unique_id_config = dish_leaf_node.TrackStop()

    # group_callback["longRunningCommandResult"].assert_change_event(
    #     (unique_id_config[0], COMMAND_COMPLETED),
    #     lookahead=6,
    # )
    # group_callback["pointingState"].assert_change_event(
    #     (PointingState.READY),
    #     lookahead=5,
    # )
    # group_callback["dishMode"].assert_change_event(
    #     (DishMode.OPERATE),
    #     lookahead=5,
    # )
    # dish_leaf_node.unsubscribe_event(DISHMODE_ID)
    dish_leaf_node.unsubscribe_event(POINTINGSTATE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)


# @pytest.mark.sah1589
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
