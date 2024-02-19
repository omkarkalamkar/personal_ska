import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode

from tests.settings import DISH_LEAF_NODE_DEVICE, DISH_MASTER_DEVICE, event_remover, logger


def off_command(tango_context, dishln_name, group_callback):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.OPERATE)
    dish_master.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=2,
    )
    event_remover(
        group_callback,
        ["longRunningCommandsInQueue", "longRunningCommandResult"],
    )
    dish_leaf_node.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandsInQueue"],
    )
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        (),
    )

    result, unique_id = dish_leaf_node.Off()
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        ("Off",),
        lookahead=2,
    )

    logger.info(f"Command ID: {unique_id} Returned result: {result}")
    assert result[0] == ResultCode.QUEUED

    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=2,
    )

    group_callback["longRunningCommandsInQueue"].assert_change_event(
        (),
        lookahead=2,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_off_command(tango_context, group_callback):
    off_command(tango_context, DISH_LEAF_NODE_DEVICE, group_callback)
