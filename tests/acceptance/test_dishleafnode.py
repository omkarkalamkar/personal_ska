# pylint: disable=fixme
import time

import pytest
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
    assert dish_leaf_node._liveliness_probe._thread.is_alive()


@then(parsers.parse("the ping information gets updated"))
def ping_updates(dish_leaf_node):
    time.sleep(SLEEP_TIME)
    assert dish_leaf_node._device.ping > 0


# TODO: Uncomment these during testing for SetStandbyFP and SetStandbyLP mode
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
        "the command is queued and executed in less than {seconds} secs"
    )
)
def check_command(dishleaf_node, seconds):
    # TODO: Remove the with block during final testing
    with pytest.raises(AttributeError):
        if pytest.command_result == "CommandNotAllowed":
            return

        assert pytest.command_result[0][0] == ResultCode.QUEUED
        unique_id = pytest.command_result[1][0]
        start_time = time.time()
        executed = False
        while not executed:
            for command in dishleaf_node.commandExecuted:
                if command[0] == unique_id:
                    logger.info("command result: %s", command)
                    assert command[2] == str(ResultCode.OK) or command[
                        2
                    ] == str(ResultCode.FAILED)
                    executed = True
            if executed:
                break
            time.sleep(SLEEP_TIME)
            elapsed_time = time.time() - start_time
            if elapsed_time > float(seconds):
                pytest.fail("Timeout occurred while executing the test")


scenarios("../features/dishleafnode.feature")
