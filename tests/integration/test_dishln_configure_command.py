import json
from datetime import datetime
from time import sleep

import pytest
import tango
from ska_tango_base.commands import ResultCode

# from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory, DishMode, PointingState

from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    build_partial_configure_data,
    logger,
    tear_down,
)

OFFSET = 5.0


def get_non_sidereal_json_for_now(non_side_real_json) -> str:
    """Return the json for Configure command with visible non-sidereal object
    according to current time.
    """
    current_time = int(datetime.utcnow().strftime("%H"))
    configure_input_json = json.loads(non_side_real_json)
    # The data below is losely based on information found from the web, and has
    # loose limits such that elevation is >= 17.5 for the source at
    # "lat": -30.71329, "lon": 21.449412 and "h": 1098.074 for dish SKA001
    # based on TelModel-data
    if 8 <= current_time <= 14:
        configure_input_json["pointing"]["target"]["target_name"] = "Sun"
        return json.dumps(configure_input_json)
    if 3 <= current_time <= 8:
        configure_input_json["pointing"]["target"]["target_name"] = "Mars"
        return json.dumps(configure_input_json)
    if current_time <= 3 or current_time >= 21:
        configure_input_json["pointing"]["target"]["target_name"] = "Saturn"
        return json.dumps(configure_input_json)
    if 17 <= current_time <= 21:
        configure_input_json["pointing"]["target"]["target_name"] = "Pluto"
        return json.dumps(configure_input_json)
    if 14 <= current_time <= 15:
        configure_input_json["pointing"]["target"]["target_name"] = "Venus"
        return json.dumps(configure_input_json)
    return ""


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
    logger.info(
        "LONG RUNNING COMMAND RESULT is: %s",
        dish_leaf_node.longRunningCommandResult,
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
@pytest.mark.ktest
@pytest.mark.parametrize(
    "json_to_use", ["dishleafnode_configure", "non_sidereal_tracking"]
)
def test_configure_command(
    tango_context, group_callback, json_factory, json_to_use
):
    if json_to_use == "non_sidereal_tracking":
        json_to_use = get_non_sidereal_json_for_now(json_factory(json_to_use))
        configure_dish_leaf_node(
            tango_context,
            DISH_LEAF_NODE_DEVICE,
            group_callback,
            json_to_use,
        )
    else:
        configure_dish_leaf_node(
            tango_context,
            DISH_LEAF_NODE_DEVICE,
            group_callback,
            json_factory(json_to_use),
        )


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
