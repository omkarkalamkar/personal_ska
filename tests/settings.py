import logging

from ska_tmc_common.op_state_model import TMCOpStateModel
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_dishleafnode.manager.component_manager import (
    DishLNComponentManager,
)

logger = logging.getLogger(__name__)

sleep_time = 0.5
timeout = 100

dish_master_device = "mid_d0001/elt/master"


def create_cm(device):
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

    cm._dish_dev_name = dish_master_device
    command_obj = command_class(cm, cm.op_state_model, adapter_factory, logger)
    return cm, command_obj, adapter_factory
