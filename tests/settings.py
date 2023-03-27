"""This module provides settings for the test cases."""
import logging
from typing import List

from ska_tmc_common.enum import LivelinessProbeType
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_dishleafnode.manager.component_manager import (
    DishLNComponentManager,
)

logger = logging.getLogger(__name__)

SLEEP_TIME = 0.5
TIMEOUT = 100

dish_leaf_node_device = "ska_mid/tm_leaf_node/d0"
dish_master_device = "mid_d0001/elt/master"
DISH_MASTER_DEVICE = "mid_d0001/elt/master"


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
            iterable = group_callback._mock_consumer_group._views[
                attribute
            ]._iterable
            for node in iterable:
                logger.info("Payload is: %s", repr(node.payload))
                node.drop()
        except KeyError:
            pass
