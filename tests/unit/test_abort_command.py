import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.commands.abort_command import AbortCommands
from tests.settings import DISH_MASTER_DEVICE, create_cm, logger, wait_for_unresponsive


def test_abort_command(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    abort_command = AbortCommands(cm, logger=logger)
    result_code, _ = abort_command.do()
    assert result_code == ResultCode.OK


@pytest.mark.test
def test_abort_command_fail_check_allowed_with_device_unresponsive(
    tango_context,
):
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.get_device().update_unresponsive(True)
    result = wait_for_unresponsive(cm)
    if result:
        with pytest.raises(DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"):
            cm.is_abortcommands_allowed()
    else:
        raise AssertionError("Failed to check DeviceUnresponsive with abort command.")
