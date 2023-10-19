import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.commands.set_kvalue import SetKValueCommand
from tests.settings import DISH_MASTER_DEVICE, create_cm, logger


def test_set_kvalue_command(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    set_kvalue_command = SetKValueCommand(cm, logger=logger)
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK


def test__command_fail_check_allowed_with_device_unresponsive(
    tango_context,
):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.get_device().update_unresponsive(True)
    with pytest.raises(DeviceUnresponsive):
        cm.is_set_kvalue_allowed()
