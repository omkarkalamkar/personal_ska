import pytest
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.setoperatemode import SetOperateMode


def test_adapter_creation_success(tango_context, cm_without_er_lp) -> None:
    cm = cm_without_er_lp
    setoperatemode_command_obj = SetOperateMode(
        cm,
        cm.op_state_model,
        cm.adapter_factory,
    )
    result_code, message = setoperatemode_command_obj.init_adapter()
    assert result_code == ResultCode.OK
    assert message == "Adapter initialisation is successful"


@pytest.mark.mccsmln
def test_adapter_creation_timeout(tango_context, cm_without_er_lp) -> None:
    cm = cm_without_er_lp
    setoperatemode_command_obj = SetOperateMode(
        cm,
        cm.op_state_model,
        cm.adapter_factory,
    )
    cm.dish_dev_name = ""
    result_code, message = setoperatemode_command_obj.init_adapter()
    assert result_code == ResultCode.FAILED
    assert "Error in creating adapter for" in message
