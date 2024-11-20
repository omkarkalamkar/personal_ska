import pytest
from ska_tmc_common.exceptions import DeviceUnresponsive

from tests.settings import DISH_MASTER_DEVICE


def test_abort_command_fail_check_allowed_with_device_unresponsive(
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    cm.get_device().update_unresponsive(True, "Not available")
    with pytest.raises(
        DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"
    ):
        cm.is_abortcommands_allowed()


def test_trackloadstaticoff_command_not_allowed(cm_without_er_lp):
    cm = cm_without_er_lp
    """Test the command not allowed when the device is unresponsive."""
    cm.get_device().update_unresponsive(True, "Not available")
    with pytest.raises(DeviceUnresponsive):
        cm.is_trackloadstaticoff_allowed()
