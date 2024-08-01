# pylint: disable=line-too-long,unused-import

import logging
import time

import pytest
import tango
from pytest_bdd import given, parsers, scenarios, then, when
from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode, PointingState  # noqa:F401
from tango import Database, DeviceProxy

from tests.settings import COMMAND_COMPLETED, wait_for_ping

configure_logging(logging.DEBUG)
LOGGER = logging.getLogger(__name__)


@given(
    parsers.parse("DishLeafNode and DishMaster devices are running"),
    target_fixture="dishleafnode_cm",
)
def dishleafnode_cm(tango_context, cm_new):
    database = Database()
    instance_list = database.get_device_exported_for_class("DishLeafNode")
    for instance in instance_list.value_string:
        assert "ska_mid/tm_leaf_node/d" in DeviceProxy(instance).dev_name()
    return cm_new


@when(parsers.parse("DishLeafNode pings the DishMaster device"))
def ping_started(dishleafnode_cm):
    start_time = time.time()
    while not dishleafnode_cm.liveliness_probe_object._thread.is_alive():
        time.sleep(0.5)
        if time.time() - start_time > 30:
            LOGGER.info("Liveliness thread is not alive")
            break

    assert dishleafnode_cm.liveliness_probe_object._thread.is_alive()


@then(parsers.parse("the ping information gets updated"))
def ping_updates(dishleafnode_cm):
    wait_for_ping(dishleafnode_cm)
    assert dishleafnode_cm._device.ping > 0


@given(
    parsers.parse("a DishLeafNode device"),
    target_fixture="dishleaf_node",
)
def dishleaf_node():
    database = Database()
    instance_list = database.get_device_exported_for_class("DishLeafNode")
    for instance in instance_list.value_string:
        return DeviceProxy(instance)


@when(
    parsers.parse(
        "I call the command {command_name} when DishMaster is in {dish_mode}"
    )
)
def call_command(
    dishleaf_node,
    command_name,
    dish_mode,
    dish_master_device,
    group_callback,
    json_factory,
):
    try:
        dev_factory = DevFactory()
        dish_master_proxy = dev_factory.get_device(dish_master_device)
        dishMode = eval(dish_mode)
        dish_master_proxy.SetDirectDishMode(dishMode)
        dish_master_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            group_callback["dishMode"],
        )
        group_callback["dishMode"].assert_change_event(
            (dishMode),
            lookahead=8,
        )
        if command_name == "Configure":
            configure_string = json_factory("dishleafnode_configure")
            pytest.command_result = dishleaf_node.command_inout(
                command_name, configure_string
            )
        else:
            pytest.command_result = dishleaf_node.command_inout(command_name)
    except Exception as ex:
        assert "CommandNotAllowed" in str(ex)
        pytest.command_result = "CommandNotAllowed"


@then(
    parsers.parse(
        "the {command_name} command is executed successfully "
        "and DishMaster transitions to {resultant_state}"
    )
)
def check_command(
    dishleaf_node,
    resultant_state,
    group_callback,
    dish_master_device,
):
    dev_factory = DevFactory()
    dish_master_proxy = dev_factory.get_device(dish_master_device)
    if pytest.command_result == "CommandNotAllowed":
        return

    assert pytest.command_result[0][0] == ResultCode.QUEUED
    unique_id = pytest.command_result[1][0]
    LRCR_ID = dishleaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id, COMMAND_COMPLETED), lookahead=8
    )
    # Invoke TrackStop command to terminate the Track thread executed by
    # Configure command.If thread not stopped then it is causing unstable
    # device server and intermittent test failure.
    if "Configure" in unique_id:
        if (
            dishleaf_node.dishMode == DishMode.OPERATE
            and dishleaf_node.pointingState == PointingState.TRACK
        ):
            dishleaf_node.TrackStop()
    assert str(dish_master_proxy.state()) == resultant_state
    dishleaf_node.unsubscribe_event(LRCR_ID)


scenarios("../features/dishleafnode.feature")
