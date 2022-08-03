# pylint: disable=line-too-long
import time

import pytest
import tango
from pytest_bdd import given, parsers, scenarios, then, when
from ska_tango_base.commands import ResultCode
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


@when(parsers.parse("I call the command {command_name}"))
def call_command(dishleaf_node, command_name):
    try:
        pytest.command_result = dishleaf_node.command_inout(command_name)
    except Exception as ex:
        assert "CommandNotAllowed" in str(ex)
        pytest.command_result = "CommandNotAllowed"


@then(
    parsers.parse(
        "the {command_name} command is queued and executed in less than {seconds} secs"  # noqa:E501
    )
)
def check_command(dishleaf_node, command_name, seconds, group_callback):
    if pytest.command_result == "CommandNotAllowed":
        return

    assert pytest.command_result[0][0] == ResultCode.QUEUED
    unique_id = pytest.command_result[1][0]
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
    group_callback["longRunningCommandsInQueue"].assert_change_event(
        (str(command_name),),
    )
    start_time = time.time()
    executed = False
    while not executed:
        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id, str(int(ResultCode.OK))), lookahead=2
        )
        elapsed_time = time.time() - start_time
        if elapsed_time > float(seconds):
            pytest.fail("Timeout occurred while executing the test")
        else:
            executed = True

    group_callback["longRunningCommandsInQueue"].assert_change_event(
        None,
        lookahead=2,
    )


scenarios("../features/dishleafnode.feature")
