"""Integration test for testing forward and backward transform."""
import ast
import datetime
from time import sleep

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory, DishMode

from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    logger,
    tear_down,
    wait_and_validate_attribute_value_available,
    wait_for_attribute_value,
)


def forward_backward_transform(tango_context, dishln_name, configure_input_str, group_callback):
    """Execute Configure and test forward and backward transform."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_FP)
    dish_master.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    # Wait for dish leaf node CM to update dish mode
    sleep(1)
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=4,
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
    result_config, unique_id_config = dish_leaf_node.Configure(configure_input_str)
    assert result_config[0] == ResultCode.QUEUED
    group_callback["longRunningCommandsInQueue"].assert_change_event(("Configure",), lookahead=2)

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], str(int(ResultCode.OK))),
        lookahead=6,
    )
    assert wait_for_attribute_value(dish_master, "desiredPointing")

    desired_pointing = dish_master.read_attribute("desiredPointing").value
    logger.info("The desired pointing is set to %s", desired_pointing)

    # Waiting for some time, to let the Track Thread Run.
    sleep(10)

    result_trackstop, unique_id_trackstop = dish_leaf_node.TrackStop()
    assert result_trackstop[0] == ResultCode.QUEUED
    group_callback["longRunningCommandsInQueue"].assert_change_event(("TrackStop",), lookahead=4)

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_trackstop[0], str(int(ResultCode.OK))),
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


def actual_pointing_attr(tango_context):
    """Test to check actualPointing is getting updated"""
    EXTEND_MILLISECONDS = 100
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    dish_master = DevFactory().get_device(DISH_MASTER_DEVICE)
    timestamp_str = datetime.datetime.strptime("2019-02-19 06:01:00", "%Y-%m-%d %H:%M:%S")
    dt_utc = timestamp_str.replace(tzinfo=datetime.timezone.utc)
    extended_time = dt_utc + datetime.timedelta(milliseconds=EXTEND_MILLISECONDS)
    utc_timestamp = extended_time.timestamp() * 1000
    dish_master.desiredPointing = [utc_timestamp, 287.2504396, 77.8694392]
    verify_value = '["2019-02-19 06:01:00", "16:29:24.46", "-26:25:55.7"]'
    wait_and_validate_attribute_value_available(
        dish_leaf_node, "actualPointing", expected_value=verify_value
    )
    assert dish_leaf_node.actualPointing == verify_value


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_forward_backward_transform(tango_context, json_factory, group_callback):
    """Test forward and backward transform calculations."""
    forward_backward_transform(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        json_factory("dishleafnode_configure"),
        group_callback,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_actual_pointing_attribute(tango_context, json_factory, group_callback):
    """Test forward and backward transform calculations."""
    actual_pointing_attr(tango_context)
