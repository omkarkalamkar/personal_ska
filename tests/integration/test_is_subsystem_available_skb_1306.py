"""SKB-1306: isSubsystemAvailable must be True for Subarray read paths.

Run on Linux (simulator — no live Tango DB):

    poetry run pytest tests/integration/test_is_subsystem_available_skb_1306.py -v -o addopts=""

Live dish on skancra: add ``--true-context`` (requires Tango DB + exported dish).
"""

from __future__ import annotations

import time

import pytest
import tango

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")
pytest_plugins = ["tests.integration.skb_1306_fixtures"]


def _read_is_subsystem_available(proxy: tango.DeviceProxy) -> bool | None:
    try:
        attr = proxy.read_attribute("isSubsystemAvailable")
        if attr.quality == tango.AttrQuality.ATTR_VALID:
            return attr.value
    except tango.DevFailed:
        pass
    return None


def _wait_until_true(proxy: tango.DeviceProxy, timeout_s: int = 120) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _read_is_subsystem_available(proxy) is True:
            return
        time.sleep(1)
    pytest.fail(
        f"isSubsystemAvailable did not become True within {timeout_s}s "
        f"(last={_read_is_subsystem_available(proxy)})"
    )


def test_read_true_after_startup(dish_proxy: tango.DeviceProxy) -> None:
    _wait_until_true(dish_proxy)
    assert _read_is_subsystem_available(dish_proxy) is True


def test_read_true_after_subscribe(dish_proxy: tango.DeviceProxy) -> None:
    _wait_until_true(dish_proxy)

    event_id = dish_proxy.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        lambda _event: None,
    )
    try:
        time.sleep(0.5)
        assert _read_is_subsystem_available(dish_proxy) is True
    finally:
        dish_proxy.unsubscribe_event(event_id)
