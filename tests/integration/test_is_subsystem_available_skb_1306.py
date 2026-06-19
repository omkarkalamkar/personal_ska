"""Integration tests for SKB-1306 isSubsystemAvailable attribute_from_signal.

Run on Linux via:

    make python-test FILE=tests/integration/test_is_subsystem_available_skb_1306.py

These tests must not run in parallel (shared Tango device names).
"""

import time
from typing import Generator, NamedTuple

import pytest
import tango
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from ska_tmc_common.dev_factory import DevFactory
from tango.test_context import MultiDeviceTestContext

from tests.conftest import get_integration_devices_to_load
from tests.settings import DISH_LEAF_NODE_DEVICE, logger

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")


class Skb1306Availability(NamedTuple):
    """Shared availability state for all tests in this module."""

    group_callback: MockTangoEventCallbackGroup
    read_proxy: tango.DeviceProxy


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
def skb1306_availability(tango_context, request) -> Generator[Skb1306Availability, None, None]:
    """Subscribe before startup completes; poll availability on a separate proxy."""
    if request.config.getoption("--true-context"):
        pytest.skip("requires test context")

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
    time.sleep(1)

    # Do not poll on the subscribed proxy; use a fresh proxy for reads.
    read_proxy = tango.DeviceProxy(DISH_LEAF_NODE_DEVICE)
    assert _wait_for_availability(read_proxy, True), (
        "isSubsystemAvailable did not become True within timeout"
    )

    yield Skb1306Availability(group_callback, read_proxy)
    event_proxy.unsubscribe_event(event_id)


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


def test_is_subsystem_available_after_startup(
    tango_context, skb1306_availability
) -> None:
    """DishLeafNode reports dish manager availability after startup."""
    logger.info("tango_context: %s", tango_context)
    read_proxy = skb1306_availability.read_proxy

    attr = read_proxy.read_attribute("isSubsystemAvailable")
    assert attr.quality == tango.AttrQuality.ATTR_VALID
    assert read_proxy.isSubsystemAvailable is True


def test_subarray_assign_resources_read_pattern(skb1306_availability) -> None:
    """Mirror TMC Subarray add_device_to_lp synchronous attribute read."""
    availability = tango.DeviceProxy(DISH_LEAF_NODE_DEVICE).isSubsystemAvailable
    assert availability is True


def test_is_subsystem_available_change_event(skb1306_availability) -> None:
    """Subarray subscribes to isSubsystemAvailable change events."""
    skb1306_availability.group_callback["isSubsystemAvailable"].assert_change_event(
        True,
        lookahead=10,
    )
