"""Integration tests for SKB-1306 isSubsystemAvailable attribute_from_signal.

Run on Linux via:

    make python-test FILE=tests/integration/test_is_subsystem_available_skb_1306.py

These tests must not run in parallel (shared Tango device names).
"""

import time

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import DISH_LEAF_NODE_DEVICE, logger

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")


def _wait_for_availability(
    dish_leaf_node: tango.DeviceProxy,
    expected: bool,
    timeout: int = 120,
) -> bool:
    """Poll isSubsystemAvailable until expected value or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if dish_leaf_node.isSubsystemAvailable is expected:
                return True
            attr = dish_leaf_node.read_attribute("isSubsystemAvailable")
            if attr.quality == tango.AttrQuality.ATTR_VALID and attr.value is expected:
                return True
        except tango.DevFailed:
            pass
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

    availability = tango.DeviceProxy(DISH_LEAF_NODE_DEVICE).isSubsystemAvailable
    assert availability is True


def test_is_subsystem_available_subscription_read(
    tango_context, group_callback
) -> None:
    """Subarray subscribes after startup; reads must still return True."""
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    assert _wait_for_availability(dish_leaf_node, True)

    event_id = dish_leaf_node.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        group_callback["isSubsystemAvailable"],
    )
    try:
        time.sleep(0.5)
        assert tango.DeviceProxy(DISH_LEAF_NODE_DEVICE).isSubsystemAvailable is True
        assert dish_leaf_node.isSubsystemAvailable is True
    finally:
        dish_leaf_node.unsubscribe_event(event_id)
