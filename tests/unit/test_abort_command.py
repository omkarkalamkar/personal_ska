import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import PointingState
from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.commands.abort_command import AbortCommands
from tests.settings import DISH_MASTER_DEVICE, create_cm, logger


def test_abort_command(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    abort_command = AbortCommands(cm, logger=logger)
    result_code, _ = abort_command.do()
    assert result_code[0] == ResultCode.OK


def test_abort_command_fail_check_allowed_with_device_unresponsive(
    tango_context,
):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.get_device().update_unresponsive(True)
    with pytest.raises(DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"):
        cm.check_device_responsive()


def test_abort_command_device_defective(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    dev_factory = DevFactory()
    dish_device = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_device.SetDirectPointingState(PointingState.TRACK)
    assert dish_device.pointingState == PointingState.TRACK
    dish_device.SetDefective(True)
    assert dish_device.defective
    abort_command = AbortCommands(cm, logger=logger)
    result_code, _ = abort_command.do()
    assert result_code[0] == ResultCode.FAILED
