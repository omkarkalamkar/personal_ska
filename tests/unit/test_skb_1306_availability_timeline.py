"""Timeline diagnostics for isSubsystemAvailable: who changed it, who read it, when.

These tests build a millisecond-ordered trace so you can see:
- when the value was False / True
- when liveliness (simulated) ran
- when Subarray-style reads happened (before vs after)

Production Dish Leaf Node logs use the same prefix for SN/PSI correlation:

    grep 'isSubsystemAvailable trace' <dish-leaf-node-log>

Run with timeline printed on failure:

    poetry run pytest tests/unit/test_skb_1306_availability_timeline.py -v -s
"""

from __future__ import annotations

import logging
import time
from unittest.mock import MagicMock

import pytest
import tango
from ska_tango_base.software_bus import Signal, SignalBusMixin, attribute_from_signal
from ska_tmc_common.exceptions import DeviceUnresponsive
from tango import AttrWriteType
from tango.server import Device, command
from tango.test_context import DeviceTestContext

from ska_tmc_dishleafnode.dish_leaf_node import MidTmcLeafNodeDish
from tests.unit.skb_1306_availability_timeline import AvailabilityTimeline

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")


class _TraceableSignalLeafNode(SignalBusMixin, Device):
    """Minimal leaf node with traceable liveliness simulation."""

    _is_subsystem_available: Signal[bool] = Signal[bool](
        stored=True, initial_value=False
    )

    isSubsystemAvailable = attribute_from_signal(
        _is_subsystem_available,
        access=AttrWriteType.READ,
        dtype=bool,
        description="Boolean Flag for sub system available",
    )

    def init_device(self) -> None:
        super().init_device()

    @command
    def SimulateLiveliness(self, available: bool) -> None:
        """Stand in for update_availablity_callback from liveliness probe."""
        self._is_subsystem_available = available


def _subarray_read(proxy: tango.DeviceProxy, timeline: AvailabilityTimeline, label: str) -> bool:
    """Record a synchronous client read (Subarray Assign Resources pattern)."""
    value = tango.DeviceProxy(proxy.dev_name()).isSubsystemAvailable
    timeline.record("subarray", f"{label}_read", value)
    return value


def _subscribe_reads(
    proxy: tango.DeviceProxy, timeline: AvailabilityTimeline
) -> tuple[int, list[bool]]:
    received: list[bool] = []

    def _callback(event: tango.EventData) -> None:
        if not event.err:
            value = event.attr_value.value
            received.append(value)
            timeline.record("subarray", "change_event", value)

    event_id = proxy.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        _callback,
    )
    return event_id, received


def test_timeline_read_before_liveliness_shows_false_then_true() -> None:
    """Reproduce SN window: Subarray reads False before liveliness sets True."""
    timeline = AvailabilityTimeline()

    with DeviceTestContext(_TraceableSignalLeafNode, process=True) as proxy:
        timeline.record("device", "startup_complete", proxy.isSubsystemAvailable)

        event_id, _ = _subscribe_reads(proxy, timeline)
        time.sleep(0.3)
        timeline.record("subarray", "subscribed", None)

        early_read = _subarray_read(proxy, timeline, "assign_resources")
        assert early_read is False

        timeline.record("liveliness", "probe_start", None)
        proxy.SimulateLiveliness(True)
        timeline.record("liveliness", "callback_set_true", True)
        time.sleep(0.3)

        late_read = _subarray_read(proxy, timeline, "after_liveliness")
        proxy.unsubscribe_event(event_id)

    timeline.assert_order("device", "subarray", "liveliness", "subarray")
    assign_reads = [
        entry for entry in timeline.entries if entry.action == "assign_resources_read"
    ]
    after_reads = [
        entry for entry in timeline.entries if entry.action == "after_liveliness_read"
    ]
    assert assign_reads and assign_reads[0].value is False
    assert after_reads and after_reads[0].value is True

    print("\n" + timeline.format())


def test_timeline_with_init_sync_before_subarray_read() -> None:
    """With init sync, Subarray read should see True before liveliness."""
    timeline = AvailabilityTimeline()
    device = MagicMock()
    device.DishAvailabilityCheckTimeout = 1
    device._is_subsystem_available = False
    device.component_manager.check_device_responsive.return_value = None

    timeline.record("device", "startup_signal_default", device._is_subsystem_available)
    MidTmcLeafNodeDish._sync_subsystem_availability(device)
    timeline.record("init_sync", "set_true", device._is_subsystem_available)

    # Subarray read after init — no liveliness needed.
    timeline.record("subarray", "assign_resources_read", device._is_subsystem_available)

    timeline.assert_order("device", "init_sync", "subarray")
    assert timeline.entries[-1].value is True
    print("\n" + timeline.format())


def test_timeline_liveliness_false_then_true(capfd) -> None:
    """Trace dish down (False) then up (True) via liveliness callbacks."""
    timeline = AvailabilityTimeline()

    with DeviceTestContext(_TraceableSignalLeafNode, process=True) as proxy:
        timeline.record("device", "startup", proxy.isSubsystemAvailable)
        event_id, _ = _subscribe_reads(proxy, timeline)
        time.sleep(0.3)

        proxy.SimulateLiveliness(True)
        timeline.record("liveliness", "dish_up", True)
        time.sleep(0.2)
        _subarray_read(proxy, timeline, "while_up")

        proxy.SimulateLiveliness(False)
        timeline.record("liveliness", "dish_down", False)
        time.sleep(0.2)
        down_read = _subarray_read(proxy, timeline, "while_down")
        assert down_read is False

        proxy.SimulateLiveliness(True)
        timeline.record("liveliness", "dish_up_again", True)
        time.sleep(0.2)
        up_read = _subarray_read(proxy, timeline, "after_recovery")
        assert up_read is True

        proxy.unsubscribe_event(event_id)

    print("\n" + timeline.format())


def test_production_logs_emit_trace_for_init_sync(caplog) -> None:
    """Init sync writes grep-friendly trace lines to Dish Leaf Node logs."""
    caplog.set_level(logging.INFO)
    device = MagicMock()
    device.DishAvailabilityCheckTimeout = 2
    device._is_subsystem_available = False
    device.logger = logging.getLogger("test.dishln")
    device.component_manager.check_device_responsive.side_effect = [
        DeviceUnresponsive("not yet"),
        None,
    ]

    MidTmcLeafNodeDish._sync_subsystem_availability(device)

    messages = [record.message for record in caplog.records]
    assert any("init sync started" in message for message in messages)
    assert any("attempt 1/2 dish unresponsive" in message for message in messages)
    assert any("init sync set True on attempt 2/2" in message for message in messages)


def test_production_logs_emit_trace_for_liveliness_callback(caplog) -> None:
    """Doorbell callback logs previous and new availability values."""
    caplog.set_level(logging.INFO)
    device = MagicMock()
    device._is_subsystem_available = False
    device.logger = logging.getLogger("test.dishln")
    device._publish_subsystem_availability = (
        MidTmcLeafNodeDish._publish_subsystem_availability.__get__(
            device, MidTmcLeafNodeDish
        )
    )

    MidTmcLeafNodeDish.update_availablity_callback(device, True)
    MidTmcLeafNodeDish.update_availablity_callback(device, False)

    messages = [record.message for record in caplog.records]
    assert messages[0] == "isSubsystemAvailable trace: published False -> True"
    assert messages[1] == "isSubsystemAvailable trace: published True -> False"