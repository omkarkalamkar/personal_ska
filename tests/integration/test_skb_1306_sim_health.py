"""Sim health gate for SKB-1306 level-2 probes.

MultiDeviceTestContext provides the DB — no live DataBaseds needed:

    poetry run pytest tests/integration/test_skb_1306_sim_health.py -v -s -o addopts=""
"""

from __future__ import annotations

import logging
import os
import time

import pytest
import tango

from tests.settings import DISH_MASTER_DEVICE

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")
pytest_plugins = ["tests.integration.skb_1306_fixtures"]

logger = logging.getLogger(__name__)


def _log_loaded_dish_module() -> None:
    import ska_tmc_dishleafnode.dish_leaf_node as dish_mod

    logger.info("SKB-1306 sim health: dish_leaf_node=%s", dish_mod.__file__)
    logger.info("SKB-1306 sim health: TANGO_HOST=%s", os.environ.get("TANGO_HOST"))
    if hasattr(dish_mod.MidTmcLeafNodeDish, "read_isSubsystemAvailable"):
        logger.info("SKB-1306 sim health: dish impl looks like 0.45.1 (plain attribute)")
    else:
        logger.info("SKB-1306 sim health: dish impl looks like 0.45.0 (attribute_from_signal)")


def test_sim_devices_reachable(
    skb_1306_context,
    dish_proxy: tango.DeviceProxy,
) -> None:
    """Helper dish and leaf node must be exported and pingable in the sim."""
    _log_loaded_dish_module()

    dish_master = skb_1306_context.get_device(DISH_MASTER_DEVICE)
    logger.info(
        "SKB-1306 sim health: dish_master ping=%s state=%s",
        dish_master.ping(),
        dish_master.state(),
    )
    logger.info(
        "SKB-1306 sim health: dish_ln ping=%s state=%s dev_name=%s",
        dish_proxy.ping(),
        dish_proxy.state(),
        dish_proxy.dev_name(),
    )

    assert dish_master.ping() > 0, "helper dish not responding"
    assert dish_proxy.ping() > 0, "dish leaf node not responding"


def test_sim_liveliness_promotes_availability(
    dish_proxy: tango.DeviceProxy,
) -> None:
    """On 0.45.1, liveliness must drive isSubsystemAvailable reads to True."""
    import ska_tmc_dishleafnode.dish_leaf_node as dish_mod

    if not hasattr(dish_mod.MidTmcLeafNodeDish, "read_isSubsystemAvailable"):
        pytest.skip("dish_leaf_node is not 0.45.1 — liveliness True gate N/A")

    change_events: list[bool] = []

    def _on_change(event) -> None:
        if event.attr_value.quality == tango.AttrQuality.ATTR_VALID:
            change_events.append(bool(event.attr_value.value))
            logger.info(
                "SKB-1306 sim health: CHANGE_EVENT isSubsystemAvailable=%s",
                event.attr_value.value,
            )

    event_id = dish_proxy.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        _on_change,
    )
    try:
        deadline = time.time() + 90
        last: bool | None = None
        while time.time() < deadline:
            attr = dish_proxy.read_attribute("isSubsystemAvailable")
            last = (
                attr.value if attr.quality == tango.AttrQuality.ATTR_VALID else None
            )
            if last is True:
                logger.info("SKB-1306 sim health: isSubsystemAvailable True")
                return
            time.sleep(1)
    finally:
        dish_proxy.unsubscribe_event(event_id)

    pytest.fail(
        f"isSubsystemAvailable never True in 90s (last={last}, "
        f"change_events={change_events}). "
        f"Liveliness probe uses tango.Database() — ensure TANGO_HOST matches "
        f"the test context (see sync_tango_host_to_test_context). "
        f"Check logs for device_unexported / ConnectionFailed on {DISH_MASTER_DEVICE}."
    )
