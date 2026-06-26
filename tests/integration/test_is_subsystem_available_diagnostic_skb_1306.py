"""Diagnostic probes for SKB-1306 on release 0.45.0 (no production fix required).

Purpose: record what Subarray would *read* at each step. Use this on tag 0.45.0 to
capture root-cause evidence before applying any fix.

Run on Linux (e.g. skancra003) against 0.45.0:

    git checkout 0.45.0
    git checkout skb-1306-fix -- \\
        tests/integration/test_is_subsystem_available_diagnostic_skb_1306.py \\
        tests/unit/skb_1306_availability_timeline.py
    poetry run pytest \\
        tests/integration/test_is_subsystem_available_diagnostic_skb_1306.py \\
        -v -s -o addopts=""

The test always passes; read the printed timeline. Look for:
  - first read False while dish is up
  - read True then False again after subscribe (stuck read / bus replay)
"""

from __future__ import annotations

import logging
import time
from typing import Generator

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from tango.test_context import MultiDeviceTestContext

from tests.conftest import get_integration_devices_to_load
from tests.settings import DISH_LEAF_NODE_DEVICE
from tests.unit.skb_1306_availability_timeline import AvailabilityTimeline

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")

logger = logging.getLogger(__name__)


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
        DevFactory._test_context = context
        yield context


def _read_availability() -> bool | None:
    try:
        attr = tango.DeviceProxy(DISH_LEAF_NODE_DEVICE).read_attribute(
            "isSubsystemAvailable"
        )
        if attr.quality == tango.AttrQuality.ATTR_VALID:
            return attr.value
    except tango.DevFailed:
        pass
    return None


def _probe(timeline: AvailabilityTimeline, action: str) -> bool | None:
    value = _read_availability()
    timeline.record("client", action, value)
    logger.info(
        "SKB-1306 probe t=+%.0fms %s value=%s",
        timeline.entries[-1].elapsed_ms,
        action,
        value,
    )
    return value


def test_probe_read_timeline_through_startup_and_two_subscribes(
    tango_context,
) -> None:
    """Record isSubsystemAvailable reads through startup and two subscribe cycles."""
    timeline = AvailabilityTimeline()
    _probe(timeline, "immediate_after_context_start")

    first_true_ms: float | None = None
    deadline = time.time() + 60
    poll = 0
    while time.time() < deadline:
        poll += 1
        value = _probe(timeline, f"startup_poll_{poll}")
        if value is True and first_true_ms is None:
            first_true_ms = timeline.entries[-1].elapsed_ms
            break
        time.sleep(1)

    _probe(timeline, "pre_subscribe_1")
    proxy1 = tango.DeviceProxy(DISH_LEAF_NODE_DEVICE)
    event_id_1 = proxy1.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        lambda _event: None,
    )
    try:
        time.sleep(0.5)
        _probe(timeline, "post_subscribe_1_read")
    finally:
        proxy1.unsubscribe_event(event_id_1)

    _probe(timeline, "between_subscribes")
    proxy2 = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    event_id_2 = proxy2.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        lambda _event: None,
    )
    try:
        time.sleep(0.5)
        _probe(timeline, "post_subscribe_2_read")
    finally:
        proxy2.unsubscribe_event(event_id_2)

    report = timeline.format()
    logger.info("SKB-1306 integration probe report:\n%s", report)

    if first_true_ms is not None:
        logger.info(
            "SKB-1306 probe: first True read at +%.0fms", first_true_ms
        )
    else:
        logger.warning("SKB-1306 probe: never read True within 60s")

    for label in ("post_subscribe_1_read", "post_subscribe_2_read"):
        entries = [e for e in timeline.entries if e.action == label]
        if entries and entries[-1].value is False:
            logger.warning(
                "SKB-1306 probe: %s returned False (likely root-cause window)",
                label,
            )
