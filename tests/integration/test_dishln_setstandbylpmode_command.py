import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import logger


def setstandbylpmode_command(tango_context, dishln_name, group_callback):
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

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    assert result_fp == ResultCode.QUEUED
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        ("SetStandbyFPMode",),
    )
    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], str(int(ResultCode.OK))),
        lookahead=2,
    )

    result_lp, unique_id_lp = dish_leaf_node.SetStandbyLPMode()
    assert result_lp[0] == ResultCode.QUEUED
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        (
            "SetStandbyFPMode",
            "SetStandbyLPMode",
        ),
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_lp[0], str(int(ResultCode.OK))),
        lookahead=2,
    )
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
        lookahead=3,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_setstandbylpmode_command(tango_context, group_callback):
    setstandbylpmode_command(
        tango_context, "ska_mid/tm_leaf_node/d0001", group_callback
    )
