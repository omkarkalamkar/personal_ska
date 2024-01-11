import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DevState

from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    KVALUE,
    wait_and_validate_device_attribute_value,
)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_kvalue_when_dln_initialized():
    # Scenario 1: Start the device and check k-value when DLN initialized
    dev_factory = DevFactory()
    dish_leaf_node_server = dev_factory.get_device("dserver/dish_leaf_node/01")
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    dish_leaf_node.SetKValue(0)  # Set k-value to initialization value
    dish_leaf_node_server.RestartServer()
    assert wait_and_validate_device_attribute_value(
        dish_leaf_node,
        "kValueValidationResult",
        "not set",
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_kvalue_after_dln_restart():
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    # dserver/
    dish_leaf_node_server = dev_factory.get_device("dserver/dish_leaf_node/01")
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    result_fp, _ = dish_leaf_node.SetKValue(KVALUE)
    assert result_fp == ResultCode.OK
    # validate kvalue set on dish manager
    assert dish_master.kValue == dish_leaf_node.kValue
    # Scenario 2: restart the device and check k-value is identical
    dish_leaf_node_server.RestartServer()
    assert wait_and_validate_device_attribute_value(
        dish_leaf_node,
        "kValueValidationResult",
        "identical",
    )
    # Scenario 3: restart the device and check k-value is not identical
    dish_master.SetKValue(KVALUE + 1)
    dish_leaf_node_server.RestartServer()
    assert wait_and_validate_device_attribute_value(
        dish_leaf_node,
        "kValueValidationResult",
        "not identical",
    )

    assert wait_and_validate_device_attribute_value(
        dish_leaf_node,
        "State",
        DevState.ON,
    )
