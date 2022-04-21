import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import logger, sleep_time, timeout


def setstandbylpmode_command(tango_context, dishln_name):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    initial_len = len(dish_leaf_node.commandExecuted)
    (result, unique_id) = dish_leaf_node.SetStandbyLPMode()
    logger.info(result)
    logger.info(unique_id)
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(dish_leaf_node.commandExecuted) != initial_len + 1:
        time.sleep(sleep_time)
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            pytest.fail("Timeout occurred while executing the test")

    for command in dish_leaf_node.commandExecuted:
        if command[0] == unique_id[0]:
            assert command[2] == "ResultCode.OK"


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_setstandbylpmode_command(tango_context):
    setstandbylpmode_command(tango_context, "ska_mid/tm_leaf_node/d0001")
