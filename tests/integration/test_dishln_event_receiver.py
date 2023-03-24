import time

import pytest
import tango
from ska_tango_base.control_model import HealthState
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode, PointingState

from tests.settings import logger


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_dish_mode_event(dish_master_device):
    pytest.num_events_arrived = 0

    def event_callback(event):
        assert not event.err
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
        logger.info("Waiting events: %s", pytest.num_events_arrived)
        time.sleep(0.5)
        elapsed_time = time.time() - start_time
        if elapsed_time > 20:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.num_events_arrived >= 1
    dish_master.unsubscribe_event(event_id)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_pointing_state_event(dish_master_device):
    pytest.num_events_arrived = 0

    def event_callback(event):
        assert not event.err
        pytest.num_events_arrived += 1

    dev_factory = DevFactory()
    dish_master = dev_factory.get_device(dish_master_device)
    dish_master.SetDirectPointingState(PointingState.TRACK)
    time.sleep(0.1)
    event_id = dish_master.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    start_time = time.time()
    while pytest.num_events_arrived < 1:
        logger.info("Waiting events: %s", pytest.num_events_arrived)
        time.sleep(0.5)
        elapsed_time = time.time() - start_time
        if elapsed_time > 20:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.num_events_arrived >= 1
    dish_master.unsubscribe_event(event_id)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_health_state_event(dish_master_device):
    pytest.num_events_arrived = 0

    def event_callback(event: tango.EventData):
        assert not event.err
        pytest.num_events_arrived += 1

    dev_factory = DevFactory()
    dish_master = dev_factory.get_device(dish_master_device)
    dish_master.SetDirectHealthState(HealthState.OK)
    time.sleep(0.1)
    event_id = dish_master.subscribe_event(
        "healthState",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    start_time = time.time()
    while pytest.num_events_arrived < 1:
        logger.info("Waiting events: %s", pytest.num_events_arrived)
        time.sleep(0.5)
        elapsed_time = time.time() - start_time
        if elapsed_time > 20:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.num_events_arrived >= 1
    dish_master.unsubscribe_event(event_id)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_device_state_event(dish_master_device):
    pytest.num_events_arrived = 0

    def event_callback(event: tango.EventData):
        assert not event.err
        pytest.num_events_arrived += 1

    dev_factory = DevFactory()
    dish_master = dev_factory.get_device(dish_master_device)
    dish_master.SetDirectState(tango.DevState.ON)
    time.sleep(0.1)
    event_id = dish_master.subscribe_event(
        "State",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    start_time = time.time()
    while pytest.num_events_arrived < 1:
        logger.info("Waiting events: %s", pytest.num_events_arrived)
        time.sleep(0.5)
        elapsed_time = time.time() - start_time
        if elapsed_time > 20:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.num_events_arrived >= 1
    dish_master.unsubscribe_event(event_id)
