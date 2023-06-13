"""This module provides settings for the test cases."""
import logging
import time
from typing import List

from ska_tmc_common.enum import LivelinessProbeType
from ska_tmc_common.test_helpers.helper_adapter_factory import HelperAdapterFactory

from ska_tmc_dishleafnode.manager.component_manager import DishLNComponentManager

logger = logging.getLogger(__name__)

SLEEP_TIME = 0.5
TIMEOUT = 100

DISH_MASTER_DEVICE = "ska001/dish/master"
DISH_LEAF_NODE_DEVICE = "ska_mid/tm_leaf_node/d0001"


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
        _liveliness_probe=LivelinessProbeType.SINGLE_DEVICE,
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
