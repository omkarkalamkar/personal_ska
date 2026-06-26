"""Sim health gate for SKB-1306 level-2 probes.

    export TANGO_HOST=127.0.0.1:10000
    poetry run pytest tests/integration/test_skb_1306_sim_health.py -v -s -o addopts=""
"""

from __future__ import annotations

import logging
import os
import time

import pytest
import tango

from tests.settings import DISH_LEAF_NODE_DEVICE, DISH_MASTER_DEVICE

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")
pytest_plugins = ["tests.integration.skb_1306_fixtures"]

logger = logging.getLogger(__name__)


def _log_loaded_dish_module() -> None:
    import ska_tmc_dishleafnode.dish_leaf_node as dish_mod

    logger.info("SKB-1306 sim health: dish_leaf_node=%s", dish_mod.__file__)
    logger.info("SKB-1306 sim health: TANGO_HOST=%s", os.environ.get("TANGO_HOST"))


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
        "SKB-1306 sim health: dish_ln ping=%s state=%s",
        dish_proxy.ping(),
        dish_proxy.state(),
    )

    db = tango.Database()
    for name in (DISH_LEAF_NODE_DEVICE, DISH_MASTER_DEVICE):
        info = db.get_device_info(name)
        logger.info(
            "SKB-1306 sim health: %s exported=%s server=%s",
            name,
            info.exported,
            info.server,
        )
        assert info.exported, f"{name} not exported in test database"


def test_sim_liveliness_promotes_availability(
    dish_proxy: tango.DeviceProxy,
) -> None:
    """On 0.45.1, liveliness must drive isSubsystemAvailable reads to True."""
    deadline = time.time() + 90
    last: bool | None = None
    while time.time() < deadline:
        attr = dish_proxy.read_attribute("isSubsystemAvailable")
        last = attr.value if attr.quality == tango.AttrQuality.ATTR_VALID else None
        if last is True:
            logger.info("SKB-1306 sim health: isSubsystemAvailable True")
            return
        time.sleep(1)

    pytest.fail(
        "isSubsystemAvailable never True in 90s (last=%s). "
        "Liveliness is not promoting availability — check device server logs "
        "for ConnectionFailed / device_unexported on %s",
        last,
        DISH_MASTER_DEVICE,
    )
