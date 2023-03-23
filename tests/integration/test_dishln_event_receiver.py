import time

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode

from tests.settings import logger


@pytest.mark.SKA_DM
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
