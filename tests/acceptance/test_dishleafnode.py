import time

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from ska_tango_base.commands import ResultCode
from tango import Database, DeviceProxy

from tests.settings import logger, sleep_time


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
        "the command is queued and executed in less than {seconds} ss"
    )
)
def check_command(dishleaf_node, seconds):
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
                assert command[2] == str(ResultCode.OK) or command[2] == str(
                    ResultCode.FAILED
                )
                executed = True
        if executed:
            break
        time.sleep(sleep_time)
        elapsed_time = time.time() - start_time
        if elapsed_time > float(seconds):
            pytest.fail("Timeout occurred while executing the test")


scenarios("../features/dishleafnode.feature")
