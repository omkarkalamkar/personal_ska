from unittest import mock

from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.track_command import Track


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
