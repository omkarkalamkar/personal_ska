"""SKB-1306: isSubsystemAvailable must be True for Subarray read paths.

Run on Linux:

    poetry run pytest tests/integration/test_is_subsystem_available_skb_1306.py -v -o addopts=""

Keep attribute_from_signal (0.45.0). Subarray must not see a stuck False after startup
or after subscribing to change events.
"""

from __future__ import annotations

import time
from typing import Generator

import pytest
import tango
from tango.test_context import MultiDeviceTestContext

from tests.conftest import get_integration_devices_to_load
from tests.settings import DISH_LEAF_NODE_DEVICE

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")


@pytest.fixture(scope="module")
def tango_context(request) -> Generator:
    if request.config.getoption("--true-context"):
        yield None
        return

    with MultiDeviceTestContext(
        get_integration_devices_to_load(),
        process=True,
        timeout=60,
    ) as context:
        yield context


def _read_is_subsystem_available() -> bool | None:
    """Fresh proxy read, same as Subarray Assign Resources."""
    try:
        attr = tango.DeviceProxy(DISH_LEAF_NODE_DEVICE).read_attribute(
            "isSubsystemAvailable"
        )
        if attr.quality == tango.AttrQuality.ATTR_VALID:
            return attr.value
    except tango.DevFailed:
        pass
    return None


def _wait_until_true(timeout_s: int = 120) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _read_is_subsystem_available() is True:
            return
        time.sleep(1)
    pytest.fail(
        f"isSubsystemAvailable did not become True within {timeout_s}s "
        f"(last={_read_is_subsystem_available()})"
    )


def test_read_true_after_startup(tango_context) -> None:
    """After startup, synchronous read must return True (Assign Resources path)."""
    _wait_until_true()
    assert _read_is_subsystem_available() is True


def test_read_true_after_subscribe(tango_context) -> None:
    """After subscribing to change events, synchronous read must still return True."""
    _wait_until_true()

    proxy = tango.DeviceProxy(DISH_LEAF_NODE_DEVICE)
    event_id = proxy.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        lambda _event: None,
    )
    try:
        time.sleep(0.5)
        assert _read_is_subsystem_available() is True
    finally:
        proxy.unsubscribe_event(event_id)
