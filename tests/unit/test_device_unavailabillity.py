import pytest
from ska_tmc_common import DevFactory

from ska_tmc_dishleafnode.dish_leaf_node import DishLeafNode
from tests.settings import DISH_LEAF_NODE_DEVICE, logger


def test_check_device_availabillity(dishln_device):
    assert dishln_device.isSubsystemAvailable
