import pytest
import tango
from ska_tango_base.commands import ResultCode
from tango.test_utils import DeviceTestContext

from ska_tmc_dishleafnode.dish_leaf_node import DishLeafNode


@pytest.fixture
def dish_leaf_node_device(request):
    """Create DeviceProxy for tests"""
    true_context = request.config.getoption("--true-context")
    if not true_context:
        with DeviceTestContext(DishLeafNode) as proxy:
            yield proxy
    else:
        database = tango.Database()
        instance_list = database.get_device_exported_for_class("DishLeafNode")
        for instance in instance_list.value_string:
            yield tango.DeviceProxy(instance)
            break


@pytest.mark.temp
def test_commands(dish_leaf_node_device):
    result_code, _ = dish_leaf_node_device.SetStandbyFPMode()
    assert result_code[0] == ResultCode.QUEUED
