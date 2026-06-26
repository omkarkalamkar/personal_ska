"""Device list for SKB-1306 integration tests (works on 0.45.0 and later).

Self-contained so tests do not depend on helpers added after tag 0.45.0.
"""

from __future__ import annotations

from ska_tmc_simulators.helper_dish_device import HelperDishDevice
from ska_tmc_simulators.helper_sdp_queue_connector_device import (
    HelperSdpQueueConnector,
)
from tango.test_context import MultiDeviceTestContext

from ska_dishln_pointing_device.dishln_pointing_device import DishPointingDevice
from ska_tmc_dishleafnode import MidTmcLeafNodeDish
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    DISHLN_POINTING_DEVICE,
    SDP_QUEUE_CONNECTOR_DEVICE,
    SDP_QUEUE_CONNECTOR_DEVICE2,
)


def skb_1306_devices_to_load() -> tuple:
    """MultiDeviceTestContext configuration for dish leaf node integration."""
    properties = {
        "MidDishControl": DISH_MASTER_DEVICE,
        "MidPointingDevice": DISHLN_POINTING_DEVICE,
    }
    # Present on skb-1306-fix conftest; harmless if class ignores unknown props on 0.45.0
    properties.setdefault("DishAvailabilityCheckTimeout", 30)

    return (
        {
            "class": MidTmcLeafNodeDish,
            "devices": [{"name": DISH_LEAF_NODE_DEVICE, "properties": properties}],
        },
        {
            "class": DishPointingDevice,
            "devices": [{"name": DISHLN_POINTING_DEVICE}],
        },
        {
            "class": HelperDishDevice,
            "devices": [{"name": DISH_MASTER_DEVICE}],
        },
        {
            "class": HelperSdpQueueConnector,
            "devices": [
                {"name": SDP_QUEUE_CONNECTOR_DEVICE},
                {"name": SDP_QUEUE_CONNECTOR_DEVICE2},
            ],
        },
    )


def skb_1306_tango_context(timeout: int = 60) -> MultiDeviceTestContext:
    context = MultiDeviceTestContext(
        skb_1306_devices_to_load(),
        process=True,
        timeout=timeout,
    )
    context.enable_test_context_tango_host_override = True
    return context
