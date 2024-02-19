from ska_tmc_common import DevFactory

from tests.settings import DISH_LEAF_NODE_DEVICE


def test_check_device_availabillity(tango_context):
    dishln_device = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    assert dishln_device.isSubsystemAvailable
