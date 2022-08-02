import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import logger


def setstowmode_command(tango_context, dishln_name, group_callback):
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

    result, unique_id = dish_leaf_node.SetStandbyLPMode()
    assert result[0] == ResultCode.QUEUED
    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    result_stow, unique_id_stow = dish_leaf_node.SetStowMode()

    group_callback["longRunningCommandsInQueue"].assert_change_event(
        (
            "SetStandbyLPMode",
            "SetStowMode",
        ),
        lookahead=2,
    )
    logger.info(f"Command ID: {unique_id_stow} Returned result: {result_stow}")

    next_result = group_callback[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], str(int(ResultCode.OK))),
    )

    logger.info(f"attr value : {next_result['attribute_value']}")

    next_result = group_callback[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id_stow[0], str(int(ResultCode.OK))), lookahead=2
    )
    logger.info(f"attr value : {next_result['attribute_value']}")

    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
        lookahead=3,
    )


def abort_setstowmode_command(tango_context, dishln_name, group_callback):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_leaf_node.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandsInQueue"],
    )

    group_callback.assert_change_event(
        "longRunningCommandsInQueue",
        None,
    )
    dish_leaf_node.SetStandbyLPMode()
    dish_leaf_node.SetStowMode()
    group_callback.assert_change_event(
        "longRunningCommandsInQueue",
        (
            "SetStandbyLPMode",
            "SetStowMode",
        ),
        lookahead=2,
    )
    result, message = dish_leaf_node.AbortCommands()
    assert result == ResultCode.STARTED
    assert message[0] == "Aborting commands"
    group_callback.assert_change_event(
        "longRunningCommandsInQueue", None, lookahead=3
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_setstowmode_command(tango_context, group_callback):
    setstowmode_command(
        tango_context, "ska_mid/tm_leaf_node/d0001", group_callback
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_abort_setstowmode_command(tango_context, group_callback):
    abort_setstowmode_command(
        tango_context, "ska_mid/tm_leaf_node/d0001", group_callback
    )
