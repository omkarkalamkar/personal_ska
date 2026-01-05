import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode

from ska_tmc_dishleafnode.enums.stow_status import StowStatus
from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    WEATHER_STATION_DEVICE,
    logger,
    tear_down,
)


def setstowmode_command(tango_context, dishln_name, group_callback):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_FP)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=2,
    )

    result, unique_id = dish_leaf_node.SetStandbyLPMode()
    assert result[0] == ResultCode.QUEUED
    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )
    result_stow, unique_id_stow = dish_leaf_node.SetStowMode()

    logger.info(f"Command ID: {unique_id_stow} Returned result: {result_stow}")

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], COMMAND_COMPLETED),
        lookahead=2,
    )

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)


def stow_while_configuring(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )

    assert result_fp[0] == ResultCode.QUEUED
    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=5,
    )

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )
    # if dish_leaf_node.pointingState != PointingState.READY:
    #     group_callback["pointingState"].assert_change_event(
    #         (PointingState.READY),
    #         lookahead=6,
    #     )

    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )

    result_stow, unique_id_stow = dish_leaf_node.SetStowMode()
    logger.info(f"Command ID: {unique_id_stow} Returned result: {result_stow}")

    assert result_stow == ResultCode.STARTED

    group_callback["dishMode"].assert_change_event(
        (DishMode.STOW),
        lookahead=6,
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_stow[0], COMMAND_COMPLETED),
        lookahead=5,
    )

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)

    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.new2
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_stow_while_configuring(tango_context, group_callback, json_factory):
    stow_while_configuring(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
    )


@pytest.mark.new
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_setstowmode_command(tango_context, group_callback):
    setstowmode_command(tango_context, DISH_LEAF_NODE_DEVICE, group_callback)


@pytest.mark.skip(reason="inprogress")
def test_auto_stow(group_callback):
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    wms = dev_factory.get_device(WEATHER_STATION_DEVICE)
    wms.adminMode = 0
    dish_leaf_node.subscribe_event(
        "stowStatus",
        tango.EventType.CHANGE_EVENT,
        group_callback["stowStatus"],
    )
    group_callback["stowStatus"].assert_change_event(
        StowStatus.WIND_STOW_STARTED,
        lookahead=5,
    )
    group_callback["stowStatus"].assert_change_event(
        StowStatus.WIND_STOW_COMPLETED,
        lookahead=5,
    )
