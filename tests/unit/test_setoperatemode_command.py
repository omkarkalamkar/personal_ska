from ska_tango_base.commands import ResultCode
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_dishleafnode.commands.setoperatemode import SetOperateMode
from tests.settings import create_cm, get_dishln_command_obj


def test_setoperatemode_command(tango_context, dish_master_device):
    _, set_operate_mode_command, adapter_factory = get_dishln_command_obj(
        SetOperateMode
    )
    assert set_operate_mode_command.check_allowed()
    (result_code, _) = set_operate_mode_command.do()
    assert result_code == ResultCode.OK
    adapter = adapter_factory.get_or_create_adapter(dish_master_device)
    adapter.proxy.SetOperateMode.assert_called_once_with()


def test_setoperatemode_command_with_exception(
    tango_context, dish_master_device
):
    cm = create_cm(dish_master_device)
    adapter_factory = HelperAdapterFactory()
    cm.dish_dev_name = dish_master_device

    # include exception in SetOperateMode command
    adapter_factory.get_or_create_adapter(
        dish_master_device, attrs={"SetOperateMode.side_effect": Exception}
    )
    set_operate_mode_command = SetOperateMode(
        cm, cm.op_state_model, adapter_factory
    )
    assert set_operate_mode_command.check_allowed()
    (result_code, message) = set_operate_mode_command.do()
    assert result_code == ResultCode.FAILED
    assert dish_master_device in message
