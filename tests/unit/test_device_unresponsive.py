import pytest
from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.dish_leaf_node import DishLeafNode
from tests.settings import DISH_MASTER_DEVICE, logger


@pytest.fixture()
def devices_to_load():
    """Returns helper state devices."""
    return (
        {
            "class": DishLeafNode,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/d0001"},
            ],
        },
    )


def test_abort_command_fail_check_allowed_with_device_unresponsive(
    tango_context, cm
):
    logger.info("%s", tango_context)
    cm.get_device().update_unresponsive(True, "Not available")
    with pytest.raises(
        DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"
    ):
        cm.is_abortcommands_allowed()


def test_trackloadstaticoff_command_not_allowed(tango_context, cm):
    """Test the command not allowed when the device is unresponsive."""
    cm.get_device().update_unresponsive(True, "Not available")
    with pytest.raises(DeviceUnresponsive):
        cm.is_trackloadstaticoff_allowed()
