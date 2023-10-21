import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.commands.abort_command import AbortCommands
from tests.settings import DISH_MASTER_DEVICE, create_cm, logger


def test_abort_command(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    abort_command = AbortCommands(cm, logger=logger)
    result_code, _ = abort_command.do()
    assert result_code == ResultCode.OK


def test_abort_command_fail_check_allowed_with_device_unresponsive(
    tango_context,
):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.get_device().update_unresponsive(True)
    wait_for_unresponsive(cm)
    with pytest.raises(DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"):
        cm.is_abortcommands_allowed()


def wait_for_unresponsive(cm):
    """Waits for device unresponsive update to True."""
    start_time = time.time()
    elapsed_time = 0
    timeout = 50
    while elapsed_time < timeout:
        if cm.get_device()._unresponsive:
            return True
        elapsed_time = time.time() - start_time
    return False
