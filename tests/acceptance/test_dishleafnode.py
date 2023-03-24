# pylint: disable=line-too-long
import time

import pytest
import tango
from pytest_bdd import given, parsers, scenarios, then, when
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode  # noqa:F401
from tango import Database, DeviceProxy

from tests.settings import SLEEP_TIME, create_cm


@given(
    parsers.parse("DishLeafNode and DishMaster devices are running"),
    target_fixture="dishleafnode_cm",
)
def dishleafnode_cm(tango_context, dish_master_device):
    database = Database()
    instance_list = database.get_device_exported_for_class("DishLeafNode")
    for instance in instance_list.value_string:
        assert "ska_mid/tm_leaf_node/d" in DeviceProxy(instance).dev_name()
    cm = create_cm(dish_master_device)
    return cm


@when(parsers.parse("DishLeafNode pings the DishMaster device"))
def ping_started(dishleafnode_cm):
    assert dishleafnode_cm.liveliness_probe_object._thread.is_alive()


@then(parsers.parse("the ping information gets updated"))
def ping_updates(dishleafnode_cm):
    time.sleep(SLEEP_TIME)
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
    dishleaf_node, command_name, dish_mode, dish_master_device, group_callback
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
            (dish_mode),
            lookahead=2,
        )
        pytest.command_result = dishleaf_node.command_inout(command_name)
    except Exception as ex:
        assert "CommandNotAllowed" in str(ex)
        pytest.command_result = "CommandNotAllowed"


@then(
    parsers.parse(
        "the {command_name} command is executed successfully and DishMaster transitions to {resultant_state}"  # noqa:E501
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
    dishleaf_node.subscribe_event(
        "longRunningCommandIDsInQueue",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandIDsInQueue"],
    )

    dishleaf_node.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandsInQueue"],
    )
    dishleaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["longRunningCommandIDsInQueue"].assert_change_event(
        (str(unique_id),),
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id, str(int(ResultCode.OK))), lookahead=2
    )

    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
        lookahead=2,
    )
    assert str(dish_master_proxy.state()) == resultant_state


scenarios("../features/dishleafnode.feature")
