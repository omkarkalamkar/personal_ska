import json
from unittest import mock

import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory

from ska_tmc_dishleafnode.commands.track_command import Track
from ska_tmc_dishleafnode.enums import CapabilityStates
from tests.settings import DISH_MASTER_DEVICE


def test_adapter_creation_success(cm_without_er_lp) -> None:
    cm = cm_without_er_lp
    dishMock = mock.Mock()
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    track_command_obj = Track(
        cm, cm.op_state_model, adapter_factory, logger=cm.logger
    )
    track_command_obj._adapter_factory = adapter_factory
    result_code, message = track_command_obj.init_adapter()
    assert result_code == ResultCode.OK
    assert message == "Adapter initialisation is successful"


def test_adapter_creation_timeout(cm_without_er_lp) -> None:
    cm = cm_without_er_lp
    track_command_obj = Track(
        cm, cm.op_state_model, cm.adapter_factory, logger=cm.logger
    )
    track_command_obj._adapter_factory = cm.adapter_factory
    cm.dish_dev_name = ""
    result_code, message = track_command_obj.init_adapter()
    assert result_code == ResultCode.FAILED
    assert "Error in creating adapter for" in message


def test_band_capability_state_change(
    cm_without_er_lp, group_callback, tango_context
) -> None:
    cm = cm_without_er_lp
    dish_device = DevFactory().get_device(DISH_MASTER_DEVICE)
    cm.get_device()._unresponsive = False
    assert cm.is_trackloadstaticoff_allowed()
    dish_device.subscribe_event(
        "b1CapabilityState",
        tango.EventType.CHANGE_EVENT,
        group_callback["b1CapabilityState"],
        stateless=True,
    )
    dish_device.subscribe_event(
        "b2CapabilityState",
        tango.EventType.CHANGE_EVENT,
        group_callback["b2CapabilityState"],
        stateless=True,
    )
    # Simulate band capability state change
    capability_argin = {
        "B1": CapabilityStates.OPERATE_FULL,
        "B2": CapabilityStates.OPERATE_DEGRADED,
    }
    dish_device.SetDirectCapabilityState(json.dumps(capability_argin))
    group_callback["b1CapabilityState"].assert_change_event(
        CapabilityStates.OPERATE_FULL,
        lookahead=5,
    )
