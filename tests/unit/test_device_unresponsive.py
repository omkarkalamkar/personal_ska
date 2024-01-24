import pytest
from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.dish_leaf_node import DishLeafNode
from tests.settings import DISH_MASTER_DEVICE, create_cm, logger, wait_for_unresponsive


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
    tango_context,
):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    wait_for_unresponsive(cm)
    with pytest.raises(DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"):
        cm.is_abortcommands_allowed()


def test_trackloadstaticoff_command_not_allowed(dish_master_device):
    """Test the command not allowed when the device is unresponsive."""
    cm = create_cm(dish_master_device)
    with pytest.raises(DeviceUnresponsive):
        cm.is_trackloadstaticoff_allowed()
