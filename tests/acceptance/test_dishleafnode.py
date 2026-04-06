# pylint: disable=line-too-long,unused-import


import pytest
import tango
from pytest_bdd import given, parsers, scenarios, then, when
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode, PointingState  # noqa:F401
from tango import Database, DeviceProxy

from tests.settings import COMMAND_COMPLETED, logger


@given(
    parsers.parse("a DishLeafNode device"),
    target_fixture="dishleaf_node",
)
def dishleaf_node():
    database = Database()
    instance_list = database.get_device_exported_for_class(
        "MidTmcLeafNodeDish"
    )
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
        logger.info("Dish Mode is %s", dish_master_proxy.dishMode)
        pytest.lrcr_event_id = dishleaf_node.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            group_callback["longRunningCommandResult"],
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
            dish_master_proxy.subscribe_event(
                "pointingState",
                tango.EventType.CHANGE_EVENT,
                group_callback["pointingState"],
            )

            result_trackstop, unique_id_trackstop = dishleaf_node.TrackStop()
            assert result_trackstop[0] == ResultCode.QUEUED

            group_callback["longRunningCommandResult"].assert_change_event(
                (unique_id_trackstop[0], COMMAND_COMPLETED),
                lookahead=6,
            )

            group_callback["pointingState"].assert_change_event(
                (PointingState.READY),
                lookahead=6,
            )

    if "Configure" in unique_id:
        assert dish_master_proxy.dishMode == DishMode.OPERATE
    else:
        assert dish_master_proxy.dishMode in (
            DishMode.STANDBY_LP,
            DishMode.STANDBY_FP,
        )
    dishleaf_node.unsubscribe_event(pytest.lrcr_event_id)


scenarios("../features/dishleafnode.feature")
