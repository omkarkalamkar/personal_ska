import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import logger


# Modification in test case to use ska-tango-testing's Mock callback class
def setstandbyfpmode_command(tango_context, dishln_name, group_callback):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_leaf_node.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandsInQueue"],
    )
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
    )

    result, unique_id = dish_leaf_node.SetStandbyFPMode()
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        ("SetStandbyFPMode",),
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
        None,
        lookahead=2,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_on_command(tango_context, group_callback):
    setstandbyfpmode_command(
        tango_context, "ska_mid/tm_leaf_node/d0001", group_callback
    )
