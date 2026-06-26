"""Unit probe reproducing 0.45.0 isSubsystemAvailable (signal-only callback).

Runs without full dish stack — shows attribute_from_signal + callback that only
assigns the signal (no explicit push), matching tag 0.45.0.

    poetry run pytest tests/unit/test_is_subsystem_available_diagnostic_0450.py -v -s -o addopts=""
"""

from __future__ import annotations

import logging
import time

import pytest
import tango
from ska_tango_base.software_bus import Signal, SignalBusMixin, attribute_from_signal
from tango import AttrWriteType
from tango.server import Device, command
from tango.test_context import DeviceTestContext

from tests.unit.skb_1306_availability_timeline import AvailabilityTimeline

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")

logger = logging.getLogger(__name__)


class _DishLeaf0450Probe(SignalBusMixin, Device):
    """Minimal 0.45.0 pattern: attribute_from_signal + signal-only callback."""

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
    def SimulateLivelinessTrue(self) -> None:
        """Same as 0.45.0 update_availablity_callback(True) — signal assign only."""
        self._is_subsystem_available = True


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
        "SKB-1306 unit probe t=+%.0fms %s value=%s",
        timeline.entries[-1].elapsed_ms,
        action,
        value,
    )
    return value


def test_unit_probe_0450_signal_only_callback() -> None:
    """Timeline: False at startup, True after liveliness, check read after subscribe."""
    timeline = AvailabilityTimeline()

    with DeviceTestContext(_DishLeaf0450Probe, process=True) as proxy:
        _probe(timeline, proxy, "after_device_start")
        time.sleep(0.5)
        _probe(timeline, proxy, "after_500ms_before_liveliness")

        proxy.SimulateLivelinessTrue()
        time.sleep(0.3)
        _probe(timeline, proxy, "after_liveliness_set_true")

        fresh = tango.DeviceProxy(proxy.dev_name())
        _probe(timeline, fresh, "fresh_proxy_after_liveliness")

        event_id = fresh.subscribe_event(
            "isSubsystemAvailable",
            tango.EventType.CHANGE_EVENT,
            lambda _event: None,
        )
        try:
            time.sleep(0.5)
            _probe(timeline, fresh, "after_subscribe_read")
        finally:
            fresh.unsubscribe_event(event_id)

    logger.info("SKB-1306 unit probe report:\n%s", timeline.format())

    startup_false = any(
        e.action == "after_device_start" and e.value is False
        for e in timeline.entries
    )
    if startup_false:
        logger.info("SKB-1306 unit probe: startup read False (expected on 0.45.0)")

    after_live = next(
        (e for e in timeline.entries if e.action == "after_liveliness_set_true"),
        None,
    )
    after_sub = next(
        (e for e in timeline.entries if e.action == "after_subscribe_read"),
        None,
    )
    if after_live and after_live.value is True and after_sub and after_sub.value is False:
        logger.warning(
            "SKB-1306 unit probe: True after liveliness but False after subscribe "
            "(matches integration root cause)"
        )
