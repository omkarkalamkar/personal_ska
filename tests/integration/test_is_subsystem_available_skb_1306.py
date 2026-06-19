"""Integration tests for SKB-1306 isSubsystemAvailable attribute_from_signal.

These tests use MultiDeviceTestContext (via the tango_context fixture) with
DishLeafNode + Dish Manager simulators. They are intended to run in CI via
`make python-test` on Linux.

Do NOT run with pytest-forked on macOS: fork after Tango/CORBA threads start
causes segfaults (fork-unsafe on macOS).
"""

import time

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import DISH_LEAF_NODE_DEVICE, logger


def _wait_for_availability(
    dish_leaf_node: tango.DeviceProxy,
    expected: bool,
    timeout: int = 60,
) -> bool:
    """Poll isSubsystemAvailable until expected value or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        attr = dish_leaf_node.read_attribute("isSubsystemAvailable")
        if attr.quality == tango.AttrQuality.ATTR_VALID and attr.value is expected:
            return True
        time.sleep(1)
    return False


def test_is_subsystem_available_after_startup(tango_context) -> None:
    """DishLeafNode reports dish manager availability after startup."""
    logger.info("tango_context: %s", tango_context)
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)

    assert _wait_for_availability(dish_leaf_node, True), (
        "isSubsystemAvailable did not become True within timeout"
    )

    attr = dish_leaf_node.read_attribute("isSubsystemAvailable")
    assert attr.quality == tango.AttrQuality.ATTR_VALID
    assert dish_leaf_node.isSubsystemAvailable is True


def test_subarray_assign_resources_read_pattern(tango_context) -> None:
    """Mirror TMC Subarray add_device_to_lp synchronous attribute read."""
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)

    assert _wait_for_availability(dish_leaf_node, True)

    # Same read path used by SubarrayNodeComponentManagerMid.add_device_to_lp
    availability = tango.DeviceProxy(DISH_LEAF_NODE_DEVICE).isSubsystemAvailable
    assert availability is True


def test_is_subsystem_available_change_event(tango_context, group_callback) -> None:
    """Subarray subscribes to isSubsystemAvailable change events."""
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)

    assert _wait_for_availability(dish_leaf_node, True)

    event_id = dish_leaf_node.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        group_callback["isSubsystemAvailable"],
    )
    try:
        group_callback["isSubsystemAvailable"].assert_change_event(
            True,
            lookahead=2,
        )
    finally:
        dish_leaf_node.unsubscribe_event(event_id)
