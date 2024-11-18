import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DevState

from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    KVALUE,
    dln_can_communicate_with_dish_master,
    wait_and_validate_attribute_value_available,
)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_kvalue_when_dln_initialized(tango_context, group_callback):
    """Note: Its observed that frequent running of this test case makes the
    k8s pod unstable due to restart which results in test case failure."""
    # Scenario 1: Start the device and check k-value when DLN initialized
    dev_factory = DevFactory()
    dish_leaf_node_server = dev_factory.get_device("dserver/dish_leaf_node/01")
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    dish_leaf_node.SetKValue(0)  # Set k-value to initialization value
    dish_leaf_node_server.RestartServer()
    assert wait_and_validate_attribute_value_available(
        dish_leaf_node,
        "kValueValidationResult",
        str(int(ResultCode.UNKNOWN)),
    )
    KVALUE_ID = dish_leaf_node.subscribe_event(
        "kValueValidationResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["kValueValidationResult"],
    )
    group_callback["kValueValidationResult"].assert_change_event(
        str(int(ResultCode.UNKNOWN)),
        lookahead=8,
    )
    dish_leaf_node.unsubscribe_event(KVALUE_ID)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_kvalue_identical_after_dln_restart(tango_context, group_callback):
    """Note: Its observed that frequent running of this test case makes the
    k8s pod unstable due to restart which results in test case failure."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    dish_leaf_node_server = dev_factory.get_device("dserver/dish_leaf_node/01")
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    result_code, _ = dish_leaf_node.SetKValue(KVALUE)
    assert result_code == ResultCode.OK
    # validate kvalue set on dish manager
    assert dish_master.kValue == dish_leaf_node.kValue
    # Scenario 2: restart the device and check k-value is identical

    dish_leaf_node_server.RestartServer()
    assert wait_and_validate_attribute_value_available(
        dish_leaf_node,
        "State",
        DevState.ON,
    )
    assert wait_and_validate_attribute_value_available(
        dish_leaf_node,
        "kValueValidationResult",
        str(int(ResultCode.OK)),
    )
    KVALUE_VAL_ID = dish_leaf_node.subscribe_event(
        "kValueValidationResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["kValueValidationResult"],
    )
    group_callback["kValueValidationResult"].assert_change_event(
        str(int(ResultCode.OK)),
        lookahead=8,
    )

    KVALUE_ID = dish_leaf_node.subscribe_event(
        "kValue",
        tango.EventType.CHANGE_EVENT,
        group_callback["kValue"],
    )
    group_callback["kValue"].assert_change_event(
        dish_leaf_node.kValue,
        lookahead=8,
    )
    dish_leaf_node.unsubscribe_event(KVALUE_ID)
    dish_leaf_node.unsubscribe_event(KVALUE_VAL_ID)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_kvalue_not_identical_after_dln_restart(tango_context, group_callback):
    """Note: Its observed that frequent running of this test case makes the
    k8s pod unstable due to restart which results in test case failure."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    dish_leaf_node_server = dev_factory.get_device("dserver/dish_leaf_node/01")
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    result_code, _ = dish_leaf_node.SetKValue(KVALUE)
    assert result_code == ResultCode.OK
    # validate kvalue set on dish manager
    assert dish_master.kValue == dish_leaf_node.kValue

    # Scenario 3: restart the device and check k-value is not identical
    dish_master.SetKValue(KVALUE + 1)
    dish_leaf_node_server.RestartServer()
    assert wait_and_validate_attribute_value_available(
        dish_leaf_node,
        "State",
        DevState.ON,
    )
    assert wait_and_validate_attribute_value_available(
        dish_leaf_node,
        "kValueValidationResult",
        str(int(ResultCode.FAILED)),
    )
    KVALUE_ID = dish_leaf_node.subscribe_event(
        "kValueValidationResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["kValueValidationResult"],
    )
    group_callback["kValueValidationResult"].assert_change_event(
        str(int(ResultCode.FAILED)),
        lookahead=8,
    )
    dish_leaf_node.unsubscribe_event(KVALUE_ID)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_kvalue_dln_restart_dm_unavailable(tango_context, group_callback):
    """Note: Its observed that frequent running of this test case makes the
    k8s pod unstable due to restart which results in test case failure.
    dm = dish manager"""
    db = tango.Database()
    dev_info = tango.DbDevInfo()
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    dish_leaf_node_server = dev_factory.get_device("dserver/dish_leaf_node/01")
    dish_master_server = dev_factory.get_device("dserver/mocks/01")
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    result_code, _ = dish_leaf_node.SetKValue(KVALUE)
    assert result_code == ResultCode.OK
    # validate kvalue set on dish manager
    assert dish_master.kValue == dish_leaf_node.kValue

    # Scenario 4: restart DLN and dish manager not unavailable
    # Make the dish master unavailable
    db.delete_device(DISH_MASTER_DEVICE)
    dish_leaf_node_server.RestartServer()
    wait_and_validate_attribute_value_available(
        dish_leaf_node,
        "State",
        DevState.ON,
    )
    assert wait_and_validate_attribute_value_available(
        dish_leaf_node,
        "kValueValidationResult",
        str(int(ResultCode.NOT_ALLOWED)),
    )
    KVALUE_ID = dish_leaf_node.subscribe_event(
        "kValueValidationResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["kValueValidationResult"],
    )
    group_callback["kValueValidationResult"].assert_change_event(
        str(int(ResultCode.NOT_ALLOWED)),
        lookahead=8,
    )
    dish_leaf_node.unsubscribe_event(KVALUE_ID)
    dev_info.name = DISH_MASTER_DEVICE
    dev_info.server = "mocks/01"
    dev_info._class = "HelperDishDevice"
    db.add_device(dev_info)
    dish_master_server.RestartServer()
    wait_and_validate_attribute_value_available(
        dish_master, "State", DevState.DISABLE, timeout=30
    )
    # check the devices are stable and available for further testing.
    assert dln_can_communicate_with_dish_master(dish_leaf_node)
    assert dish_leaf_node.kValue == dish_master.kValue
