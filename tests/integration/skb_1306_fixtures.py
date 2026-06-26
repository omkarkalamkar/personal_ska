"""Shared fixtures for SKB-1306 integration probes."""

from __future__ import annotations

from typing import Generator

import pytest
import tango

from tests.integration.skb_1306_test_devices import skb_1306_tango_context
from tests.settings import DISH_LEAF_NODE_DEVICE


@pytest.fixture(scope="module")
def skb_1306_context(request) -> Generator:
    """In-process sim (default) or None when --true-context reads the live dish."""
    if request.config.getoption("--true-context"):
        yield None
        return

    with skb_1306_tango_context(timeout=60) as context:
        yield context


@pytest.fixture(scope="module")
def dish_proxy(request, skb_1306_context) -> tango.DeviceProxy:
    """Live DB device (--true-context) or sim device from MultiDeviceTestContext."""
    if request.config.getoption("--true-context"):
        return tango.DeviceProxy(DISH_LEAF_NODE_DEVICE)
    return skb_1306_context.get_device(DISH_LEAF_NODE_DEVICE)
