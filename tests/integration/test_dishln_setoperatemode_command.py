import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import logger


def setoperatemode_command(tango_context, dishln_name, group_callback):
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

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    group_callback.assert_change_event(
        "longRunningCommandsInQueue",
        ("SetStandbyFPMode",),
    )
    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback.assert_change_event(
        "longRunningCommandResult",
        (unique_id_fp[0], str(int(ResultCode.OK))),
    )

    assert result_fp[0] == ResultCode.QUEUED
    result_op, unique_id_op = dish_leaf_node.SetOperateMode()
    group_callback.assert_change_event(
        "longRunningCommandsInQueue",
        (
            "SetStandbyFPMode",
            "SetOperateMode",
        ),
        lookahead=2,
    )
    logger.info(f"Command ID: {unique_id_op} Returned result: {result_op}")
    assert result_op[0] == ResultCode.QUEUED

    group_callback.assert_change_event(
        "longRunningCommandResult",
        (unique_id_op[0], str(int(ResultCode.OK))),
        lookahead=4,
    )
    group_callback.assert_change_event(
        "longRunningCommandsInQueue",
        None,
        lookahead=3,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_setoperatemode_command(tango_context, group_callback):
    setoperatemode_command(
        tango_context, "ska_mid/tm_leaf_node/d0001", group_callback
    )
