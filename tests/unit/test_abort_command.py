import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode, PointingState
from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.commands.abort_command import Abort
from tests.settings import DISH_MASTER_DEVICE, create_cm, logger


@pytest.mark.SKA_mid
def test_abort_command(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    abort_command = Abort(cm, logger=logger)
    result_code, _ = abort_command.do()
    assert result_code == ResultCode.OK


def test_abort_command_incorrect_dishmode(tango_context):
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.update_device_dish_mode(DishMode.STANDBY_LP)
    abort_command = Abort(cm, logger=logger)
    result_code, message = abort_command.stop_dish_tracking()
    assert result_code == ResultCode.FAILED


def test_abort_command_incorrect_pointingstate(tango_context):
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.update_device_pointing_state(PointingState.NONE)
    abort_command = Abort(cm, logger=logger)
    result_code, message = abort_command.stop_dish_tracking()
    assert result_code == ResultCode.FAILED


def test_abort_command_fail_check_allowed_with_device_unresponsive(
    tango_context,
):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.get_device().update_unresponsive(True)
    with pytest.raises(DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"):
        cm.check_device_responsive()
