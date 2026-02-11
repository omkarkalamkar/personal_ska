import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import DISH_LEAF_NODE_DEVICE


def set_kvalue_command():
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    # result_fp, _ = dish_leaf_node.SetKValue(1)

    result_fp, msg = dish_leaf_node.SetKValue(1)

    print("SetKValue result_fp:", result_fp)
    print("SetKValue message :", msg)
    print("kValue attribute  :", dish_leaf_node.kValue)

    # assert result_fp[0] == ResultCode.QUEUED
    # assert dish_leaf_node.kValue == 1
    assert dish_leaf_node.kValue == 1
    assert result_fp == ResultCode.OK


@pytest.mark.test_kvalue
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_set_kvalue_command():
    set_kvalue_command()
