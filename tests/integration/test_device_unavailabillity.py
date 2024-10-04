import pytest
from ska_tmc_common import DevFactory

from tests.settings import DISH_LEAF_NODE_DEVICE


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_check_device_availabillity():
    dishln_device = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    assert dishln_device.isSubsystemAvailable
