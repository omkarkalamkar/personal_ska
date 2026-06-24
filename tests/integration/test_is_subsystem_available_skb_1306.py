"""Integration tests for SKB-1306 isSubsystemAvailable attribute_from_signal.

Run on Linux via:

    make python-test FILE=tests/integration/test_is_subsystem_available_skb_1306.py

Correlate with Dish Leaf Node trace logs (same t=+ms origin at device init):

    grep 'isSubsystemAvailable trace' <dish-leaf-node-log>

These tests must not run in parallel (shared Tango device names).
"""

from __future__ import annotations

import time
from typing import Generator

import pytest
import tango
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from ska_tmc_common.dev_factory import DevFactory
from tango.test_context import MultiDeviceTestContext

from tests.conftest import get_integration_devices_to_load
from tests.settings import DISH_LEAF_NODE_DEVICE, logger
from tests.unit.skb_1306_availability_timeline import AvailabilityTimeline

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")


@pytest.fixture(scope="module")
def tango_context(request) -> Generator:
    """Start devices once; restarting between tests races on shared names."""
    if request.config.getoption("--true-context"):
        yield None
        return

    with MultiDeviceTestContext(
        get_integration_devices_to_load(),
        process=True,
        timeout=60,
    ) as context:
        DevFactory._test_context = context
        yield context


@pytest.fixture(scope="module", autouse=True)
def wait_for_initial_availability(tango_context, request) -> None:
    """Wait once after context startup before any test runs."""
    if request.config.getoption("--true-context"):
        return
    time.sleep(2)
    assert _wait_for_availability(DISH_LEAF_NODE_DEVICE, True, timeout=180), (
        "isSubsystemAvailable did not become True after module startup"
    )


def _read_availability(device_name: str) -> bool | None:
    """Read isSubsystemAvailable from server; None if not valid yet."""
    try:
        attr = tango.DeviceProxy(device_name).read_attribute("isSubsystemAvailable")
        if attr.quality == tango.AttrQuality.ATTR_VALID:
            return attr.value
    except tango.DevFailed:
        pass
    return None


def _wait_for_availability(
    device_name: str,
    expected: bool,
    timeout: int = 120,
) -> bool:
    """Poll isSubsystemAvailable until expected value or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = _read_availability(device_name)
        if value is expected:
            return True
        time.sleep(1)
    return False


def _assert_availability_read(
    device_name: str,
    expected: bool,
    attempts: int = 10,
    pause_s: float = 0.5,
) -> None:
    """Assert a fresh server read matches expected, with short retries."""
    last: bool | None = None
    for _ in range(attempts):
        last = _read_availability(device_name)
        if last is expected:
            return
        time.sleep(pause_s)
    pytest.fail(
        f"isSubsystemAvailable read did not become {expected} "
        f"after {attempts} attempts (last={last})"
    )


def test_is_subsystem_available_after_startup(tango_context) -> None:
    """DishLeafNode reports dish manager availability after startup."""
    logger.info("tango_context: %s", tango_context)
    _assert_availability_read(DISH_LEAF_NODE_DEVICE, True)


def test_subarray_assign_resources_read_pattern(tango_context) -> None:
    """Mirror TMC Subarray add_device_to_lp synchronous attribute read."""
    _assert_availability_read(DISH_LEAF_NODE_DEVICE, True)


def test_is_subsystem_available_subscription_read(tango_context) -> None:
    """Subarray subscribes after startup; reads must still return True."""
    _assert_availability_read(DISH_LEAF_NODE_DEVICE, True)

    group_callback = MockTangoEventCallbackGroup(
        "isSubsystemAvailable",
        timeout=80,
    )
    event_proxy = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    event_id = event_proxy.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        group_callback["isSubsystemAvailable"],
    )
    try:
        time.sleep(0.5)
        _assert_availability_read(DISH_LEAF_NODE_DEVICE, True)
    finally:
        event_proxy.unsubscribe_event(event_id)


def test_availability_startup_timeline(tango_context) -> None:
    """Log startup reads, then subscribe and confirm reads stay True."""
    timeline = AvailabilityTimeline()
    timeline.record("device", "context_ready", None)

    deadline = time.monotonic() + 30
    index = 0
    while time.monotonic() < deadline:
        value = _read_availability(DISH_LEAF_NODE_DEVICE)
        timeline.record("subarray", f"pre_subscribe_read_{index}", value)
        if value is True:
            break
        index += 1
        time.sleep(0.25)

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
        time.sleep(0.5)
        post_value = _read_availability(DISH_LEAF_NODE_DEVICE)
        timeline.record("subarray", "post_subscribe_read", post_value)
    finally:
        dish_leaf_node.unsubscribe_event(event_id)

    logger.info("SKB-1306 startup timeline:\n%s", timeline.format())
    logger.info(
        "Compare with dish log: grep 'isSubsystemAvailable trace' <dish-leaf-node-log>"
    )
    true_reads = [entry for entry in timeline.entries if entry.value is True]
    assert true_reads, f"Never read True.\n{timeline.format()}"
    assert any(
        entry.action == "post_subscribe_read" and entry.value is True
        for entry in timeline.entries
    ), f"Read False after subscribe.\n{timeline.format()}"
