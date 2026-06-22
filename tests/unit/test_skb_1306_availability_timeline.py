"""Timeline diagnostics for isSubsystemAvailable timing (SKB-1306).

Run with timeline printed on failure:

    poetry run pytest tests/unit/test_skb_1306_availability_timeline.py -v -s
"""

from __future__ import annotations

import time

import pytest
import tango
from ska_tango_base.software_bus import Signal, SignalBusMixin, attribute_from_signal
from tango import AttrWriteType
from tango.server import Device, command
from tango.test_context import DeviceTestContext

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
