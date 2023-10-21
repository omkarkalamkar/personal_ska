import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue
from tests.settings import DISH_MASTER_DEVICE, create_cm, logger


def test_set_kvalue_command(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    set_kvalue_command = SetKValue(cm, logger=logger)
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK


@pytest.mark.debug
def test_command_fail_check_allowed_with_device_unresponsive(
    tango_context,
):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.get_device().update_unresponsive(True)
    wait_for_unresponsive(cm)
    with pytest.raises(DeviceUnresponsive):
        cm.is_set_kvalue_allowed()


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
