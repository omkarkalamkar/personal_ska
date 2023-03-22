import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode

from tests.settings import event_remover, logger


def setstandbyfpmode_command(tango_context, dishln_name, group_callback):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
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
def test_on_command(tango_context, group_callback):
    setstandbyfpmode_command(
        tango_context, "ska_mid/tm_leaf_node/d0001", group_callback
    )


@pytest.mark.TEST_DM
def test_dm(dish_master_device):
    pytest.num_events_arrived = 0

    def event_callback(evt):
        assert not evt.err
        pytest.num_events_arrived += 1

    dev_factory = DevFactory()
    dish_master = dev_factory.get_device(dish_master_device)
    dish_master.SetDirectDishMode(DishMode.OPERATE)
    time.sleep(0.1)
    event_id = dish_master.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    start_time = time.time()
    while pytest.num_events_arrived < 1:
        logger.info("waiting events: %s", pytest.num_events_arrived)
        time.sleep(0.5)
        elapsed_time = time.time() - start_time
        if elapsed_time > 20:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.num_events_arrived >= 1
    dish_master.unsubscribe_event(event_id)
