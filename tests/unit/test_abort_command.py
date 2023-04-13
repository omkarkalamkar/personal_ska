import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.commands.abort_command import Abort
from tests.settings import DISH_MASTER_DEVICE, get_dishln_command_obj, logger


@pytest.mark.SKA_mid
def test_abort_command(tango_context):
    logger.info("%s", tango_context)
    _, abort_command, adapter_factory = get_dishln_command_obj(Abort)
    (result_code, _) = abort_command.invoke_abort_commands()
    assert result_code == ResultCode.OK
    adapter = adapter_factory.get_or_create_adapter(DISH_MASTER_DEVICE)
    adapter.proxy.AbortCommands.assert_called_once_with()


def test_abort_command_fail_check_allowed_with_device_unresponsive(
    tango_context,
):
    logger.info("%s", tango_context)
    cm, _, _ = get_dishln_command_obj(Abort)
    cm.get_device().update_unresponsive(True)
    with pytest.raises(
        DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"
    ):
        cm.check_device_responsive()
