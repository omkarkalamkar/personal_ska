import json
import time
from time import sleep

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory, DishMode, PointingState

from tests.settings import (  # event_remover,
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    build_partial_configure_data,
    logger,
    tear_down,
)

OFFSET = 5.0


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


def unhappy_configure_command(
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

    # This is needed since we want to exeute test case 10 times.
    dish_master.SetDirectConfiguredBand(1)
    sleep(1)

    # dish_master.subscribe_event(
    #     "dishMode",
    #     tango.EventType.CHANGE_EVENT,
    #     group_callback["dishMode"],
    # )
    # dish_master.subscribe_event(
    #     "pointingState",
    #     tango.EventType.CHANGE_EVENT,
    #     group_callback["pointingState"],
    # )

    # group_callback["dishMode"].assert_change_event(
    #     (DishMode.STANDBY_LP),
    #     lookahead=2,
    # )
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

    # Send second configure command

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )

    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    pytest.command_result = group_callback[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id_config[0], Anything),
        lookahead=6,
    )

    assert "Already in band" in pytest.command_result["attribute_value"][1]
    result_config, unique_id_config = dish_leaf_node.TrackStop()

    time.sleep(1)

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=9,
    )

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )

    # group_callback["longRunningCommandsInQueue"].assert_change_event(
    #     (),
    #     lookahead=8,
    # )
    dish_leaf_node.unsubscribe_event(DISHMODE_ID)
    dish_leaf_node.unsubscribe_event(POINTINGSTATE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)
    tear_down(dish_leaf_node, dish_master, group_callback)


def partial_configure_dish_leaf_node(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
    partial_configure_input_str,
):
    """Partial configure flow for dish leaf node."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    sleep(1)
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

    SOURCE_OFFSET_ID = dish_leaf_node.subscribe_event(
        "sourceOffset",
        tango.EventType.CHANGE_EVENT,
        group_callback["sourceOffset"],
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
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )
    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    partial_configurations = build_partial_configure_data(
        partial_configure_input_str, OFFSET
    )
    count = 0
    for input_str in partial_configurations:
        # Give a pause before invoking next configuration
        sleep(3)
        result_config, unique_id_config = dish_leaf_node.Configure(input_str)
        assert result_config[0] == ResultCode.QUEUED
        load_conf = json.loads(input_str)
        ca_offset = load_conf["pointing"]["target"]["ca_offset_arcsec"]
        ie_offset = load_conf["pointing"]["target"]["ie_offset_arcsec"]
        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id_config[0], COMMAND_COMPLETED),
            lookahead=8,
        )
        # Assert change event is occuring and values are reflecting
        # on sourceOffset attribute.
        group_callback["sourceOffset"].assert_change_event(
            [ca_offset, ie_offset],
            lookahead=2,
        )
        count += 1

    result_trackstop, unique_id_trackstop = dish_leaf_node.TrackStop()
    assert result_trackstop[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_trackstop[0], COMMAND_COMPLETED),
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

    dish_leaf_node.unsubscribe_event(SOURCE_OFFSET_ID)
    dish_leaf_node.unsubscribe_event(DISHMODE_ID)
    dish_leaf_node.unsubscribe_event(POINTINGSTATE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)
    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_partial_configure_command(
    tango_context, group_callback, json_factory
):
    """Test partial configure functionality on Dish Leaf Node."""
    partial_configure_dish_leaf_node(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
        json_factory("partial_configure"),
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_configure_command(tango_context, group_callback, json_factory):
    configure_dish_leaf_node(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_unhappy_configure_command(
    tango_context, group_callback, json_factory
):
    unhappy_configure_command(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure_band2"),
    )
