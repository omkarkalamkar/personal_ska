import pytest
from ska_tmc_common.exceptions import DeviceUnresponsive

from tests.settings import DISH_MASTER_DEVICE


def test_abort_command_fail_check_allowed_with_device_unresponsive(
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    cm.get_device(cm.dish_dev_name).update_unresponsive(True, "Not available")
    with pytest.raises(
        DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"
    ):
        cm.is_abort_allowed()
