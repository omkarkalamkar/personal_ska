import json

import pytest
import tango
from ska_tmc_common import DevFactory

from ska_tmc_dishleafnode.enums import CapabilityStates
from tests.settings import DISH_MASTER_DEVICE


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_dishln_band_capability(group_callback):
    dish_manager_device = DevFactory().get_device(DISH_MASTER_DEVICE)
    dish_manager_device.subscribe_event(
        "b1CapabilityState",
        tango.EventType.CHANGE_EVENT,
        group_callback["b1CapabilityState"],
    )
    dish_manager_device.subscribe_event(
        "b2CapabilityState",
        tango.EventType.CHANGE_EVENT,
        group_callback["b2CapabilityState"],
    )
    capabiity_argin = json.dumps(
        {
            "B1": CapabilityStates.OPERATE_FULL,
            "B2": CapabilityStates.OPERATE_DEGRADED,
        }
    )
    dish_manager_device.SetDirectCapabilityState(capabiity_argin)
    group_callback["b1CapabilityState"].assert_change_event(
        (CapabilityStates.OPERATE_FULL),
        lookahead=5,
    )
    group_callback["b2CapabilityState"].assert_change_event(
        (CapabilityStates.OPERATE_DEGRADED),
        lookahead=5,
    )
