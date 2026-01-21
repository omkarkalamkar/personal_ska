"""Test to verify EndScan command on dishleafnode"""
import json
from time import time

import pytest
import tango
from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode, PointingState

from ska_tmc_dishleafnode.enums import CapabilityStates
from tests.settings import (
    COMMAND_COMPLETED,
    COMMAND_FAILED_WITH_TRACK,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    DISHLN_POINTING_DEVICE,
    get_non_sidereal_json_for_source_unknown,
    log_and_assert_health,
    logger,
    monitor_track_table_errors_attribute,
    tear_down,
    wait_and_validate_attribute_value_available,
    wait_for_attribute_health_value,
    wait_for_attribute_value,
)


def observation_workflow(
    tango_context, dishln_name, group_callback, configure_input_str
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

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
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

    log_and_assert_health(
        dish_leaf_node,
        dish_master,
        dishln_pointing_device,
        HealthState.OK,
        None,
    )
    logger.info("Health state is OK before configure command")

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED

    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )
    group_callback["pointingState"].assert_change_event(
        (PointingState.SLEW),
        lookahead=6,
    )
    wait_and_validate_attribute_value_available(
        dish_leaf_node, "pointingState", PointingState.TRACK, timeout=30
    )
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    # After Configure Health State is OK

    log_and_assert_health(
        dish_leaf_node,
        dish_master,
        dishln_pointing_device,
        HealthState.OK,
        None,
    )

    # Requested Band becomes UNAVAILABLE
    # Hence Health moves to FAILED
    logger.info("will set CapabilityStates.UNAVAILABLE")

    capabiity_argin = json.dumps(
        {
            "B1": CapabilityStates.OPERATE_FULL,
            "B2": CapabilityStates.UNAVAILABLE,
            "B3": CapabilityStates.OPERATE_FULL,
            "B4": CapabilityStates.OPERATE_FULL,
            "B5a": CapabilityStates.OPERATE_FULL,
            "B5b": CapabilityStates.OPERATE_FULL,
        }
    )
    dish_master.SetDirectCapabilityState(capabiity_argin)
    wait_for_attribute_health_value(dish_leaf_node, "healthState", 2)
    log_and_assert_health(
        dish_leaf_node,
        dish_master,
        dishln_pointing_device,
        HealthState.FAILED,
        "Requested band B2 is in state UNAVAILABLE (not fully available)",
    )

    result_scan, unique_id_scan = dish_leaf_node.Scan("1")
    assert result_scan[0] == ResultCode.QUEUED
    logger.info(f"Command ID: {unique_id_scan} Returned result: {result_scan}")

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_scan[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    wait_for_attribute_value(dish_master, "scanID", "1")
    assert dish_master.scanID == "1"

    result_endscan, unique_id_endscan = dish_leaf_node.EndScan()
    assert result_endscan[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_endscan} Returned result: {result_endscan}"
    )

    wait_for_attribute_value(dish_master, "scanID", "1")
    assert dish_master.scanID == ""

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_endscan[0], COMMAND_COMPLETED),
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

    wait_for_attribute_health_value(dish_leaf_node, "healthState", 1)
    log_and_assert_health(
        dish_leaf_node,
        dish_master,
        dishln_pointing_device,
        HealthState.DEGRADED,
        "Unavailable bands: B2",
    )

    logger.info("Band B2 will be available again")

    # Band B2 will be available again , causing Health State to be 1

    capabiity_argin = json.dumps(
        {
            "B2": CapabilityStates.OPERATE_FULL,
        }
    )
    dish_master.SetDirectCapabilityState(capabiity_argin)
    wait_for_attribute_health_value(dish_leaf_node, "healthState", 0)
    log_and_assert_health(
        dish_leaf_node,
        dish_master,
        dishln_pointing_device,
        HealthState.OK,
        None,
    )

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)

    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_healthInfo(tango_context, group_callback, json_factory):
    observation_workflow(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
    )


# ----------------------------------------------------------
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
        "Target description 'Pluto, special' contains unknown"
        + " *special* body 'Pluto'"
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

    log_and_assert_health(
        dish_leaf_node,
        dish_master,
        dishln_pointing_device,
        HealthState.DEGRADED,
        "Target description 'Pluto, special' contains unknown ",
    )

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
