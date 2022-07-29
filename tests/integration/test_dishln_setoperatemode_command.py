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

    result, unique_id = dish_leaf_node.SetOperateMode()
    group_callback.assert_change_event(
        "longRunningCommandsInQueue",
        ("SetOperateMode",),
    )

    logger.info(f"Command ID: {unique_id} Returned result: {result}")
    assert result[0] == ResultCode.QUEUED

    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    next_result = group_callback.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=2,
    )
    logger.info(f"attr value : {next_result['attribute_value']}")

    command_id, result = next_result["attribute_value"]
    assert command_id.endswith("SetOperateMode")
    assert int(result) == ResultCode.OK
    group_callback.assert_change_event(
        "longRunningCommandsInQueue",
        None,
        lookahead=2,
    )


# @pytest.mark.skip
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_setoperatemode_command(tango_context, group_callback):
    setoperatemode_command(
        tango_context, "ska_mid/tm_leaf_node/d0001", group_callback
    )


# import time

# import pytest
# from ska_tango_base.commands import ResultCode
# from ska_tmc_common.dev_factory import DevFactory

# from tests.settings import SLEEP_TIME, TIMEOUT, logger


# def setoperatemode_command(tango_context, dishln_name):
#     logger.info(f"{tango_context}")
#     dev_factory = DevFactory()
#     dish_leaf_node = dev_factory.get_device(dishln_name)
#     initial_len = len(dish_leaf_node.commandExecuted)
#     (result, unique_id) = dish_leaf_node.SetStandbyLPMode()
#     (result, unique_id) = dish_leaf_node.SetStandbyFPMode()
#     # Add assert statement to check if it is in FP mode
#     (result, unique_id) = dish_leaf_node.SetOperateMode()
#     logger.info(f"Command ID: {unique_id} Returned result: {result}")
#     assert result[0] == ResultCode.QUEUED
#     start_time = time.time()
#     # 3 commands are getting executed above therefore check if initial length
#     # of the commandExecuted attribute has incremented by 3
#     while len(dish_leaf_node.commandExecuted) < initial_len + 3:
#         time.sleep(SLEEP_TIME)
#         elapsed_time = time.time() - start_time
#         if elapsed_time > TIMEOUT:
#             pytest.fail("Timeout occurred while executing the test")

#     for command in dish_leaf_node.commandExecuted:
#         if command[0] == unique_id[0]:
#             assert command[2] == "ResultCode.OK"


# @pytest.mark.post_deployment
# @pytest.mark.SKA_mid
# @pytest.mark.xfail(
#     reason="Need to update the command to support base class v0.13.0"
# )
# def test_setoperatemode_command(tango_context):
#     setoperatemode_command(tango_context, "ska_mid/tm_leaf_node/d0001")
