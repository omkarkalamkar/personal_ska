"""Integration tests for SKB-1306 isSubsystemAvailable attribute_from_signal.

Run on Linux via:

    make python-test FILE=tests/integration/test_is_subsystem_available_skb_1306.py

These tests must not run in parallel (shared Tango device names).
"""

import time
from typing import Generator

import pytest
import tango
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from ska_tmc_common.dev_factory import DevFactory
from tango.test_context import MultiDeviceTestContext

from tests.conftest import get_integration_devices_to_load
from tests.settings import DISH_LEAF_NODE_DEVICE, logger

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


@pytest.fixture(scope="module")
def availability_change_subscription(tango_context, request):
    """Subscribe before availability becomes True to catch the transition."""
    if request.config.getoption("--true-context"):
        pytest.skip("requires test context")

    group_callback = MockTangoEventCallbackGroup(
        "isSubsystemAvailable",
        timeout=80,
    )
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    event_id = dish_leaf_node.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        group_callback["isSubsystemAvailable"],
    )
    time.sleep(1)
    yield dish_leaf_node, group_callback, event_id
    dish_leaf_node.unsubscribe_event(event_id)


def _wait_for_availability(
    dish_leaf_node: tango.DeviceProxy,
    expected: bool,
    timeout: int = 120,
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

    availability = tango.DeviceProxy(DISH_LEAF_NODE_DEVICE).isSubsystemAvailable
    assert availability is True


def test_is_subsystem_available_change_event(
    tango_context, availability_change_subscription
) -> None:
    """Subarray subscribes to isSubsystemAvailable change events."""
    dish_leaf_node, group_callback, _event_id = availability_change_subscription

    assert _wait_for_availability(dish_leaf_node, True), (
        "isSubsystemAvailable did not become True within timeout"
    )
    group_callback["isSubsystemAvailable"].assert_change_event(
        True,
        lookahead=10,
    )
