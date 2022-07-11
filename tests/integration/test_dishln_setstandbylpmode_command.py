import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import SLEEP_TIME, TIMEOUT, logger


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
    # 1 command is getting executed above therefore check if initial length of
    # the commandExecuted attribute has incremented by 1
    while len(dish_leaf_node.commandExecuted) < initial_len + 1:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    for command in dish_leaf_node.commandExecuted:
        if command[0] == unique_id[0]:
            assert command[2] == "ResultCode.OK"


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
# @pytest.mark.xfail(
#     reason="Need to update the command to support base class v0.13.0"
# )
def test_setstandbylpmode_command(tango_context):
    setstandbylpmode_command(tango_context, "ska_mid/tm_leaf_node/d0001")
