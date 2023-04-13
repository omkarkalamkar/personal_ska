import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.exceptions import DeviceUnresponsive

from tests.settings import DISH_MASTER_DEVICE, create_cm, logger


@pytest.mark.SKA_mid
def test_abort_command(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.is_abort_allowed()
    result_code, _ = cm.abort_commands()
    assert result_code == ResultCode.OK


def test_abort_command_fail_check_allowed_with_device_unresponsive(
    tango_context,
):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.get_device().update_unresponsive(True)
    with pytest.raises(
        DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"
    ):
        cm.check_device_responsive()
