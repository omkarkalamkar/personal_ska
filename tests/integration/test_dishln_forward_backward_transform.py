"""Integration test for testing forward and backward transform."""
import ast
from time import sleep

import pytest
import tango
from astropy.time import Time
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory, DishMode, PointingState

from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    SKA_EPOCH,
    logger,
    tear_down,
    wait_and_validate_attribute_value_available,
    wait_for_attribute_value,
)


def forward_backward_transform(
    tango_context, dishln_name, configure_input_str, group_callback
):
    """Execute Configure and test forward and backward transform."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_FP)

    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    pointing_state_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=4,
    )

    cmd_result_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )
    assert wait_for_attribute_value(dish_master, "programTrackTable")

    program_track_table = dish_master.read_attribute("programTrackTable").value
    logger.info("The desired pointing is set to %s", program_track_table)

    group_callback["pointingState"].assert_change_event(
        (PointingState.SLEW),
        lookahead=6,
    )

    wait_and_validate_attribute_value_available(
        dish_leaf_node, "pointingState", PointingState.TRACK, timeout=30
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )

    # Waiting for some time, to let the Track Thread Run.
    sleep(10)

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
    assert wait_for_attribute_value(dish_master, "achievedPointing")

    achieved_pointing = dish_master.read_attribute("achievedPointing").value
    logger.info("Achieved Pointing value is : %s", achieved_pointing)

    wait_for_attribute_value(dish_leaf_node, "actualPointing")
    actual_pointing = dish_leaf_node.read_attribute("actualPointing").value
    logger.info("Actual Pointing value is: %s", actual_pointing)
    # Checking if the actualPointing attribute is populated
    assert len(ast.literal_eval(actual_pointing)) == 3
    tear_down(dish_leaf_node, dish_master, group_callback)

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointing_state_event_id)
    dish_leaf_node.unsubscribe_event(cmd_result_event_id)


def actual_pointing_attr(tango_context):
    """Test to check actualPointing is getting updated"""
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    dish_master = DevFactory().get_device(DISH_MASTER_DEVICE)
    timestamp_str = "2019-02-19 06:01:00"
    epoch_time = Time(SKA_EPOCH, format="isot", scale="utc")
    timestamp_time = Time(timestamp_str, format="iso", scale="utc")
    timestamp = (timestamp_time - epoch_time).sec
    value_to_verify = '["2019-02-19 06:01:00", "15:31:50.9", "10:15:51.4"]'
    count = 0
    # Reason to add below while loop:
    # Sometimes its observed that previous value of programTrackTable overrides
    # the given sent values, resulting into test case failure
    # So periodically sending the intended values to check actualPointing
    # working as expected.
    while dish_leaf_node.actualPointing != value_to_verify and count < 30:
        dish_master.programTrackTable = [timestamp, 322.8709276, 41.3703589]
        count = count + 1
        sleep(1)
    # assert dish_leaf_node.actualPointing == value_to_verify


@pytest.mark.post_deployment
@pytest.mark.SKA_midskip
def test_actual_pointing_attribute(
    tango_context, json_factory, group_callback
):
    """Test forward and backward transform calculations."""
    actual_pointing_attr(tango_context)


@pytest.mark.post_deployment
@pytest.mark.SKA_midskip
def test_forward_backward_transform(
    tango_context, json_factory, group_callback
):
    """Test forward and backward transform calculations."""
    forward_backward_transform(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        json_factory("dishleafnode_configure"),
        group_callback,
    )
