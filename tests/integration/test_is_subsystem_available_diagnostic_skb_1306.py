"""Diagnostic probes for SKB-1306 on release 0.45.0 (no production fix required).

Records what Subarray would *read* at each step. The test always passes; read the log.

**Simulator (no live Tango DB):**

    poetry run pytest \\
        tests/integration/test_is_subsystem_available_diagnostic_skb_1306.py \\
        -v -s -o addopts=""

**Live dish on skancra003 (--true-context needs working Tango DB + dish):**

    export TANGO_HOST=localhost:10000
    python3 -c "import tango; print(tango.Database().get_info())"
    poetry run pytest ... --true-context
"""

from __future__ import annotations

import logging
import os
import time

import pytest
import tango

from tests.settings import DISH_LEAF_NODE_DEVICE, DISH_MASTER_DEVICE
from tests.unit.skb_1306_availability_timeline import AvailabilityTimeline

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")
pytest_plugins = ["tests.integration.skb_1306_fixtures"]

logger = logging.getLogger(__name__)


def _read_availability(proxy: tango.DeviceProxy) -> bool | None:
    try:
        attr = proxy.read_attribute("isSubsystemAvailable")
        if attr.quality == tango.AttrQuality.ATTR_VALID:
            return attr.value
        logger.warning(
            "SKB-1306 probe: %s quality=%s value=%s",
            proxy.dev_name(),
            attr.quality,
            attr.value,
        )
    except tango.DevFailed as exc:
        logger.warning(
            "SKB-1306 probe: cannot read %s.isSubsystemAvailable: %s",
            proxy.dev_name(),
            exc.args[0].desc if exc.args else exc,
        )
    return None


def _probe(
    timeline: AvailabilityTimeline,
    proxy: tango.DeviceProxy,
    action: str,
) -> bool | None:
    value = _read_availability(proxy)
    timeline.record("client", action, value)
    logger.info(
        "SKB-1306 probe t=+%.0fms %s value=%s",
        timeline.entries[-1].elapsed_ms,
        action,
        value,
    )
    return value


def _log_sim_health(
    context,
    dish_proxy: tango.DeviceProxy,
) -> None:
    """Log sim connectivity when liveliness never promoted availability."""
    import ska_tmc_dishleafnode.dish_leaf_node as dish_mod

    logger.warning(
        "SKB-1306 sim health: dish_leaf_node=%s TANGO_HOST=%s",
        dish_mod.__file__,
        os.environ.get("TANGO_HOST"),
    )
    try:
        logger.warning(
            "SKB-1306 sim health: dish_ln ping=%s state=%s",
            dish_proxy.ping(),
            dish_proxy.state(),
        )
    except tango.DevFailed as exc:
        logger.warning("SKB-1306 sim health: dish_ln unreachable: %s", exc)

    try:
        dish_master = context.get_device(DISH_MASTER_DEVICE)
        logger.warning(
            "SKB-1306 sim health: dish_master ping=%s state=%s",
            dish_master.ping(),
            dish_master.state(),
        )
    except tango.DevFailed as exc:
        logger.warning("SKB-1306 sim health: dish_master unreachable: %s", exc)

    try:
        db = tango.Database()
        for name in (DISH_LEAF_NODE_DEVICE, DISH_MASTER_DEVICE):
            info = db.get_device_info(name)
            logger.warning(
                "SKB-1306 sim health: %s exported=%s server=%s",
                name,
                info.exported,
                info.server,
            )
    except tango.DevFailed as exc:
        logger.warning("SKB-1306 sim health: database check failed: %s", exc)


def test_probe_read_timeline_through_startup_and_two_subscribes(
    dish_proxy: tango.DeviceProxy,
    skb_1306_context,
    request,
) -> None:
    """Record isSubsystemAvailable reads through startup and two subscribe cycles."""
    timeline = AvailabilityTimeline()
    _probe(timeline, dish_proxy, "immediate_after_context_start")

    first_true_ms: float | None = None
    deadline = time.time() + 60
    poll = 0
    while time.time() < deadline:
        poll += 1
        value = _probe(timeline, dish_proxy, f"startup_poll_{poll}")
        if value is True and first_true_ms is None:
            first_true_ms = timeline.entries[-1].elapsed_ms
            break
        time.sleep(1)

    _probe(timeline, dish_proxy, "pre_subscribe_1")
    event_id_1 = dish_proxy.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        lambda _event: None,
    )
    try:
        time.sleep(0.5)
        _probe(timeline, dish_proxy, "post_subscribe_1_read")
    finally:
        dish_proxy.unsubscribe_event(event_id_1)

    _probe(timeline, dish_proxy, "between_subscribes")
    fresh = tango.DeviceProxy(dish_proxy.dev_name())
    event_id_2 = fresh.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        lambda _event: None,
    )
    try:
        time.sleep(0.5)
        _probe(timeline, fresh, "post_subscribe_2_read")
    finally:
        fresh.unsubscribe_event(event_id_2)

    report = timeline.format()
    logger.info("SKB-1306 integration probe report:\n%s", report)

    if first_true_ms is not None:
        logger.info(
            "SKB-1306 probe: first True read at +%.0fms", first_true_ms
        )
    else:
        logger.warning("SKB-1306 probe: never read True within 60s")
        if (
            not request.config.getoption("--true-context")
            and skb_1306_context is not None
        ):
            _log_sim_health(skb_1306_context, dish_proxy)

    for label in ("post_subscribe_1_read", "post_subscribe_2_read"):
        entries = [e for e in timeline.entries if e.action == label]
        if entries and entries[-1].value is False:
            logger.warning(
                "SKB-1306 probe: %s returned False (likely root-cause window)",
                label,
            )
