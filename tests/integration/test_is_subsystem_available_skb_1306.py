"""Integration tests for SKB-1306 isSubsystemAvailable attribute_from_signal.

Run on Linux via:

    make python-test FILE=tests/integration/test_is_subsystem_available_skb_1306.py

Correlate with Dish Leaf Node trace logs (same t=+ms origin at device init):

    grep 'isSubsystemAvailable trace' <dish-leaf-node-log>

Log sequence to compare with Subarray reads:
  device_init → init_sync → callback → signal_emission → signal_auto_push_done
  → explicit_push → subarray poll_read / change_event (from test timeline)

These tests must not run in parallel (shared Tango device names).
"""

import time

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import DISH_LEAF_NODE_DEVICE, logger
from tests.unit.skb_1306_availability_timeline import AvailabilityTimeline

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


def test_availability_startup_timeline(tango_context) -> None:
    """Poll during startup; log when first True read appears (Linux integration)."""
    timeline = AvailabilityTimeline()
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)

    def _on_change_event(event: tango.EventData) -> None:
        if event.err:
            timeline.record("subarray", "change_event_error", None)
        else:
            timeline.record("subarray", "change_event", event.attr_value.value)

    event_id = dish_leaf_node.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        _on_change_event,
    )
    try:
        timeline.record("device", "context_ready", None)
        for index in range(40):
            try:
                value = tango.DeviceProxy(DISH_LEAF_NODE_DEVICE).isSubsystemAvailable
                timeline.record("subarray", f"poll_read_{index}", value)
                if value is True:
                    break
            except tango.DevFailed:
                timeline.record("subarray", f"poll_read_{index}_failed", None)
            time.sleep(0.25)
    finally:
        dish_leaf_node.unsubscribe_event(event_id)

    logger.info("SKB-1306 startup timeline:\n%s", timeline.format())
    logger.info(
        "Compare with dish log: grep 'isSubsystemAvailable trace' <dish-leaf-node-log>"
    )
    true_reads = [entry for entry in timeline.entries if entry.value is True]
    assert true_reads, f"Never read True during startup.\n{timeline.format()}"
