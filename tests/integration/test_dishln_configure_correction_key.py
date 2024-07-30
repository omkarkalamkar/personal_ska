import json
from time import sleep

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory, DishMode, PointingState

from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    logger,
    tear_down,
)


def configure_dish_leaf_node(
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
    DISHMODE_ID = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    POINTINGSTATE_ID = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )
    group_callback["pointingState"].assert_change_event(
        (PointingState.TRACK),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )

    result_config, unique_id_config = dish_leaf_node.TrackStop()
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )
    dish_leaf_node.unsubscribe_event(DISHMODE_ID)
    dish_leaf_node.unsubscribe_event(POINTINGSTATE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)
    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize("correction", ["UPDATE", "RESET"])
def test_configure_command(
    tango_context, group_callback, json_factory, correction
):
    json_arg = json_factory("dishleafnode_configure")
    json_arg = json.loads(json_arg)
    json_arg["pointing"]["correction"] = correction
    json_arg = json.dumps(json_arg)
    configure_dish_leaf_node(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory(json_arg),
    )
