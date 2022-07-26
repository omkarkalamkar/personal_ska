# pylint: disable=line-too-long
import time

import pytest
import tango
from pytest_bdd import given, parsers, scenarios, then, when
from ska_tango_base.commands import ResultCode
from tango import Database, DeviceProxy

from tests.settings import SLEEP_TIME, create_cm, logger


@given(
    parsers.parse("DishLeafNode and DishMaster devices are running"),
    target_fixture="dish_leaf_node",
)
def dish_leaf_node(tango_context, dish_master_device):
    database = Database()
    instance_list = database.get_device_exported_for_class("DishLeafNode")
    for instance in instance_list.value_string:
        assert "ska_mid/tm_leaf_node/d" in DeviceProxy(instance).dev_name()
    cm = create_cm(dish_master_device)
    return cm


@when(parsers.parse("DishLeafNode pings the DishMaster device"))
def ping_started(dish_leaf_node):
    assert dish_leaf_node.liveliness_probe_object._thread.is_alive()


@then(parsers.parse("the ping information gets updated"))
def ping_updates(dish_leaf_node):
    time.sleep(SLEEP_TIME)
    assert dish_leaf_node._device.ping > 0


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
    group_callback.assert_change_event(
        "longRunningCommandsInQueue",
        (str(command_name),),
    )
    dishleaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    start_time = time.time()
    executed = False
    while not executed:
        next_result = group_callback.assert_against_call(
            "longRunningCommandResult"
        )
        logger.info(f"longRunningCommandResult is {next_result}")
        command_id, result = next_result["attribute_value"]
        assert command_id == unique_id
        assert int(result) == ResultCode.OK or int(result) == ResultCode.FAILED

        elapsed_time = time.time() - start_time
        if elapsed_time > float(seconds):
            pytest.fail("Timeout occurred while executing the test")
        else:
            executed = True

    group_callback.assert_change_event(
        "longRunningCommandsInQueue",
        None,
        lookahead=3,
    )


scenarios("../features/dishleafnode.feature")
