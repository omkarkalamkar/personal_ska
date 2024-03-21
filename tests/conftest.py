"""conftest module for CSP Subarray Leaf Node."""
# pylint: disable=unused-argument,redefined-outer-name
import json
import logging
from os.path import dirname, join
from time import sleep

import pytest
import tango
from ska_ser_logging.configuration import configure_logging
from ska_tango_testing.mock import MockCallable
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from ska_tmc_common import DevFactory
from ska_tmc_common.test_helpers.helper_dish_device import HelperDishDevice
from tango.test_context import DeviceTestContext, MultiDeviceTestContext

from ska_tmc_dishleafnode import DishLeafNode
from ska_tmc_dishleafnode.manager import DishLNComponentManager

configure_logging()
logger = logging.getLogger(__name__)
DISH_MASTER_DEVICE = "ska001/elt/master"


def pytest_sessionstart(session):
    """
    Pytest hook; prints info about tango version.
    :param session: a pytest Session object
    :type session: :py:class:`pytest.Session`
    """
    print(tango.utils.info())


def pytest_addoption(parser):
    """
    Pytest hook; implemented to add the `--true-context` option, used to
    indicate that a true Tango subsystem is available, so there is no
    need for a :py:class:`tango.test_context.MultiDeviceTestContext`.
    :param parser: the command line options parser
    :type parser: :py:class:`argparse.ArgumentParser`
    """
    parser.addoption(
        "--true-context",
        action="store_true",
        default=False,
        help=(
            "Tell pytest that you have a true Tango context and don't "
            "need to spin up a Tango test context"
        ),
    )


@pytest.fixture
def dish_master_device():
    """Returns dish 1 device name."""
    return "ska001/elt/master"


@pytest.fixture()
def devices_to_load():
    """Returns helper state devices."""
    return (
        {
            "class": HelperDishDevice,
            "devices": [
                {"name": "ska001/elt/master"},
            ],
        },
        {
            "class": DishLeafNode,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/d0001", "DishMasterFQDN": "ska001/elt/master"},
            ],
        },
    )


@pytest.fixture
def tango_context(devices_to_load, request):
    """Provides context to run devices without database."""
    true_context = request.config.getoption("--true-context")
    logging.info("true context: %s", true_context)
    if not true_context:
        with MultiDeviceTestContext(devices_to_load, process=False, timeout=50) as context:
            DevFactory._test_context = context
            logging.info("test context set")
            yield context
    else:
        yield None


@pytest.fixture
def dishln_device(request):
    """Create DeviceProxy for tests"""
    true_context = request.config.getoption("--true-context")
    if not true_context:
        with DeviceTestContext(
            DishLeafNode,
            device_name="ska_mid/tm_leaf_node/d0001",
            properties={"DishMasterFQDN": "ska001/elt/master", "DishAvailabilityCheckTimeout": 10},
            timeout=20,
        ) as proxy:
            yield proxy
    else:
        database = tango.Database()
        instance_list = database.get_device_exported_for_class("DishLeafNode")
        for instance in instance_list.value_string:
            yield tango.DeviceProxy(instance)
            break


@pytest.fixture
def task_callback() -> MockCallable:
    """Creates a mock callable for asynchronous testing

    :rtype: MockCallable
    """
    task_callback = MockCallable(150)
    return task_callback


@pytest.fixture
def group_callback() -> MockTangoEventCallbackGroup:
    """Creates a mock callback group for asynchronous testing

    :rtype: MockTangoEventCallbackGroup
    """
    group_callback = MockTangoEventCallbackGroup(
        "longRunningCommandsInQueue",
        "longRunningCommandResult",
        "longRunningCommandIDsInQueue",
        "longRunningCommandStatus",
        "dishMode",
        "pointingState",
        "kValueValidationResult",
        timeout=30,
    )
    return group_callback


def get_input_str(path):
    """
    Returns input json string
    :rtype: String
    """
    with open(path, "r", encoding="utf-8") as f:
        input_arg = json.load(f)
    return json.dumps(input_arg)


@pytest.fixture()
def json_factory():
    """
    Json factory for getting json files
    """

    def _get_json(slug):
        return get_input_str(join(dirname(__file__), "data", f"{slug}.json"))

    return _get_json


@pytest.fixture()
def cm() -> DishLNComponentManager:
    """Creates component manager for Dish Leaf Node."""
    cm = DishLNComponentManager(
        DISH_MASTER_DEVICE,
        logger=logger,
        track_table_entries=25,
        pointing_calculation_period=100,
        dish_availability_check_timeout=5,
        elevation_max_limit=90.0,
        elevation_min_limit=17.5,
    )
    yield cm
    # pylint: disable=unnecessary-dunder-call
    cm.__del__()
    sleep(1)  # Give some time to pytest cleanup
    # pylint: enable=unnecessary-dunder-call
