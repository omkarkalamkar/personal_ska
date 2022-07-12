"""This module provides settings for the test cases."""
import logging

from ska_tmc_common.op_state_model import TMCOpStateModel
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_dishleafnode.manager.component_manager import (
    DishLNComponentManager,
)

logger = logging.getLogger(__name__)

SLEEP_TIME = 0.5
TIMEOUT = 100

dish_master_device = "mid_d0001/elt/master"


def create_cm(device):
    """Creates component manager for CSP Subarray Leaf Node."""
    op_state_model = TMCOpStateModel(logger)
    cm = DishLNComponentManager(
        device,
        op_state_model,
        logger=logger,
    )
    return cm


def get_dishln_command_obj(command_class):
    """Returns component manager and command class object for Dish Leaf Node"""
    cm = create_cm(dish_master_device)
    adapter_factory = HelperAdapterFactory()
    cm.dish_dev_name = dish_master_device
    command_obj = command_class(cm, cm.op_state_model, adapter_factory, logger)
    return cm, command_obj, adapter_factory
