import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import SLEEP_TIME, TIMEOUT, logger


def setstandbyfpmode_command(tango_context, dishln_name):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    initial_len = len(dish_leaf_node.longRunningCommandsInQueue)
    result, unique_id = dish_leaf_node.SetStandbyFPMode()
    logger.info(f"Command ID: {unique_id} Returned result: {result}")
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    # 2 commands are getting executed above therefore check if initial length
    # of the commandExecuted attribute has incremented by 2

    while len(dish_leaf_node.longRunningCommandsInQueue) < initial_len + 1:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    command, result = dish_leaf_node.longRunningCommandResult
    if command == unique_id[0]:
        # Asserting ResultCode.OK
        assert result == "0"


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_on_command(tango_context):
    setstandbyfpmode_command(tango_context, "ska_mid/tm_leaf_node/d0001")
