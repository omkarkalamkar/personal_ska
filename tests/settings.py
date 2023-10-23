"""This module provides settings for the test cases."""
import logging
import time
from typing import Final, List

from ska_ser_logging import configure_logging
from ska_tmc_common import DishMode
from ska_tmc_common.test_helpers.helper_adapter_factory import HelperAdapterFactory
from tango import DeviceProxy

from ska_tmc_dishleafnode.manager import DishLNComponentManager

configure_logging()

logger = logging.getLogger(__name__)

SLEEP_TIME = 0.5
TIMEOUT = 100

DISH_MASTER_DEVICE = "ska001/elt/master"
DISH_LEAF_NODE_DEVICE = "ska_mid/tm_leaf_node/d0001"
WEATHER_DATA: Final = {
    "temperature": 30.0,
    "pressure": 900.0,
    "humidity": 10,
}


def wait_for_ping(dishleafnode_cm):
    """Method waits for the device ping till timeout specified
    Raises TimeoutError if the device is still unavailable within timeout.
    """
    start_time = time.time()
    elapsed_time = 0
    while dishleafnode_cm._device.ping < 0:
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            raise TimeoutError("Timeout waiting for device ping")


def create_cm(device: str) -> DishLNComponentManager:
    """Creates component manager for Dish Leaf Node."""
    cm = DishLNComponentManager(
        device,
        logger=logger,
    )
    return cm


def get_dishln_command_obj(command_class) -> tuple:
    """Returns component manager and command class object for Dish Leaf Node"""
    cm = create_cm(DISH_MASTER_DEVICE)
    adapter_factory = HelperAdapterFactory()
    cm.dish_dev_name = DISH_MASTER_DEVICE
    command_obj = command_class(cm, cm.op_state_model, adapter_factory, logger)
    return cm, command_obj, adapter_factory


def event_remover(group_callback, attributes: List[str]) -> None:
    """Removes residual events from the queue."""
    for attribute in attributes:
        try:
            iterable = group_callback._mock_consumer_group._views[attribute]._iterable
            for node in iterable:
                logger.info("Payload is: %s", repr(node.payload))
                node.drop()
        except KeyError:
            pass


def wait_for_dish_mode(cm: DishLNComponentManager, dish_mode: DishMode) -> bool:
    """Waits for dishmode to become given dish mode. Times out if the change
    does not occure. Current timeout is 10s.
    """
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time < TIMEOUT:
        if cm.dishMode == dish_mode:
            return True
        elapsed_time = time.time() - start_time
    logger.info("Current Dishmode is %s", cm.dishMode)
    return False


def wait_for_attribute_value(device: DeviceProxy, attribute_name: str, value: str = "[]") -> bool:
    """Waits for attribute value to change on the given device."""
    start_time = time.time()
    while device.read_attribute(attribute_name).value == value:
        time.sleep(0.5)
        if time.time() - start_time >= TIMEOUT:
            return False
    return True
