"""Unit probe for 0.45.1 isSubsystemAvailable (plain attribute + explicit push).

Same timeline steps as the integration diagnostic on skancra003, but without
the full dish stack — shows pre-signal / HM-903 behaviour locally.

    poetry run pytest tests/unit/test_is_subsystem_available_diagnostic_0451.py -v -s -o addopts=""
"""

from __future__ import annotations

import logging
import time

import pytest
import tango
from tango import AttrWriteType
from tango.server import Device, attribute, command
from tango.test_context import DeviceTestContext

from tests.unit.skb_1306_availability_timeline import AvailabilityTimeline

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")

logger = logging.getLogger(__name__)


class _DishLeaf0451Probe(Device):
    """Minimal 0.45.1: plain bool attribute + push on callback change."""

    def init_device(self) -> None:
        super().init_device()
        self._isSubsystemAvailable = False
        self.set_change_event("isSubsystemAvailable", True, False)
        self.set_archive_event("isSubsystemAvailable", True)

    isSubsystemAvailable = attribute(
        dtype=bool,
        access=AttrWriteType.READ,
    )

    def read_isSubsystemAvailable(self) -> bool:
        return self._isSubsystemAvailable

    @command(dtype_in=bool)
    def SimulateLiveliness(self, available: bool) -> None:
        if self._isSubsystemAvailable != available:
            self._isSubsystemAvailable = available
            with tango.EnsureOmniThread():
                self.push_change_event("isSubsystemAvailable", available)
                self.push_archive_event("isSubsystemAvailable", available)


def _read(proxy: tango.DeviceProxy) -> bool | None:
    try:
        attr = proxy.read_attribute("isSubsystemAvailable")
        if attr.quality == tango.AttrQuality.ATTR_VALID:
            return attr.value
    except tango.DevFailed:
        pass
    return None


def _probe(
    timeline: AvailabilityTimeline, proxy: tango.DeviceProxy, action: str
) -> bool | None:
    value = _read(proxy)
    timeline.record("client", action, value)
    logger.info(
        "SKB-1306 0.45.1 unit probe t=+%.0fms %s value=%s",
        timeline.entries[-1].elapsed_ms,
        action,
        value,
    )
    return value


def test_unit_probe_0451_same_timeline_as_integration() -> None:
    """Mirror integration diagnostic: startup, subscribe1, subscribe2."""
    timeline = AvailabilityTimeline()

    with DeviceTestContext(_DishLeaf0451Probe, process=True) as proxy:
        _probe(timeline, proxy, "immediate_after_context_start")

        first_true_ms: float | None = None
        for poll in range(1, 4):
            value = _probe(timeline, proxy, f"startup_poll_{poll}")
            if value is True and first_true_ms is None:
                first_true_ms = timeline.entries[-1].elapsed_ms
                break
            time.sleep(0.2)

        if first_true_ms is None:
            proxy.SimulateLiveliness(True)
            time.sleep(0.3)
            _probe(timeline, proxy, "after_forced_liveliness_true")

        _probe(timeline, proxy, "pre_subscribe_1")
        proxy1 = tango.DeviceProxy(proxy.dev_name())
        event_id_1 = proxy1.subscribe_event(
            "isSubsystemAvailable",
            tango.EventType.CHANGE_EVENT,
            lambda _event: None,
        )
        try:
            time.sleep(0.5)
            _probe(timeline, proxy1, "post_subscribe_1_read")
        finally:
            proxy1.unsubscribe_event(event_id_1)

        _probe(timeline, proxy1, "between_subscribes")
        proxy2 = tango.DeviceProxy(proxy.dev_name())
        event_id_2 = proxy2.subscribe_event(
            "isSubsystemAvailable",
            tango.EventType.CHANGE_EVENT,
            lambda _event: None,
        )
        try:
            time.sleep(0.5)
            _probe(timeline, proxy2, "post_subscribe_2_read")
        finally:
            proxy2.unsubscribe_event(event_id_2)

    report = timeline.format()
    logger.info("SKB-1306 0.45.1 unit probe report:\n%s", report)

    for label in ("post_subscribe_1_read", "post_subscribe_2_read"):
        entries = [e for e in timeline.entries if e.action == label]
        if entries and entries[-1].value is False:
            logger.warning("SKB-1306 0.45.1 unit probe: %s returned False", label)
