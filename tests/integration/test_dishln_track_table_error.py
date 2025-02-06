import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory, DishMode

from tests.settings import (
    COMMAND_COMPLETED,
    COMMAND_FAILED_WITH_TRACK,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    DISHLN_POINTING_DEVICE,
    get_non_sidereal_json_for_source_not_visible,
    get_non_sidereal_json_for_source_unknown,
    logger,
    monitor_track_table_errors_attribute,
    tear_down,
)

OFFSET = 5.0


def configure_dish_leaf_node_source_not_visible(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dishln_pointing_device = dev_factory.get_device(DISHLN_POINTING_DEVICE)
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )
    dishpd_event_id = dishln_pointing_device.subscribe_event(
        "programTrackTableError",
        tango.EventType.CHANGE_EVENT,
        group_callback["programTrackTableError"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    time.sleep(1)

    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
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

    track_table_error_before_configure = dish_leaf_node.trackTableErrors
    logger.info(
        "track_table_error_before_configure: %s",
        track_table_error_before_configure,
    )

    monitor_track_table_errors_attribute(
        dish_leaf_node, track_table_error_before_configure
    )
    expected_message = (
        "Exception occurred while calculating track table: "
        + "Minimum/maximum elevation limit has been reached."
        + "Source is not visible currently."
    )
    track_table_error = dish_leaf_node.trackTableErrors
    group_callback["programTrackTableError"].assert_change_event(
        expected_message,
        lookahead=8,
    )
    logger.info(
        "track_table_error after configure: %s",
        track_table_error,
    )
    result = any(expected_message in message for message in track_table_error)

    assert result

    group_callback["longRunningCommandResult"].assert_change_event(
        (
            unique_id_config[0],
            COMMAND_FAILED_WITH_TRACK,
        ),
        lookahead=8,
    )

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    dishln_pointing_device.unsubscribe_event(dishpd_event_id)
    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.xfail(reason="Test fails if the source is not visible.")
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize("json_to_use", ["non_sidereal_tracking"])
def test_configure_command_source_not_visible(
    tango_context, group_callback, json_factory, json_to_use
):
    json_to_use = get_non_sidereal_json_for_source_not_visible(
        json_factory(json_to_use)
    )
    configure_dish_leaf_node_source_not_visible(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_to_use,
    )


def configure_dish_leaf_node_unknown_source(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dishln_pointing_device = dev_factory.get_device(DISHLN_POINTING_DEVICE)

    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)

    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )
    dishpd_event_id = dishln_pointing_device.subscribe_event(
        "programTrackTableError",
        tango.EventType.CHANGE_EVENT,
        group_callback["programTrackTableError"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    time.sleep(1)

    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
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

    track_table_error_before_configure = dish_leaf_node.trackTableErrors
    logger.info(
        "track_table_error_before_configure: %s",
        track_table_error_before_configure,
    )
    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    monitor_track_table_errors_attribute(
        dish_leaf_node, track_table_error_before_configure
    )

    expected_message = (
        "Exception occurred while starting programTrackTable calculation: "
        + "Target description 'Pluto, special' contains unknown *special* "
        + "body 'Pluto'"
    )

    track_table_error = dish_leaf_node.trackTableErrors

    logger.info(
        "track_table_error after configure: %s",
        track_table_error,
    )
    result = any(expected_message in message for message in track_table_error)
    group_callback["programTrackTableError"].assert_change_event(
        expected_message,
        lookahead=8,
    )
    assert result

    group_callback["longRunningCommandResult"].assert_change_event(
        (
            unique_id_config[0],
            COMMAND_FAILED_WITH_TRACK,
        ),
        lookahead=8,
    )

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    dishln_pointing_device.unsubscribe_event(dishpd_event_id)
    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.xfail("Test fails randomly.It will be fixed as part of SAH-1627")
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize("json_to_use", ["non_sidereal_tracking"])
def test_configure_command_unknown_source(
    tango_context, group_callback, json_factory, json_to_use
):
    json_to_use = get_non_sidereal_json_for_source_unknown(
        json_factory(json_to_use)
    )
    configure_dish_leaf_node_unknown_source(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_to_use,
    )
