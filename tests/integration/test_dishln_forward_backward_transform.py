"""Integration test for testing forward and backward transform."""
from time import sleep

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory, DishMode

from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    logger,
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
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=2,
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
    sleep(5)

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
    assert actual_pointing


@pytest.mark.skip(reason="Will be fixed as part of HM-344")
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
