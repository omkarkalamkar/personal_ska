from time import sleep

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory, DishMode, PointingState
from tango import DeviceProxy
from tango.db import Database, DbDevInfo

from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    DISHLN_POINTING_DEVICE,
    logger,
    monitor_track_table_errors_attribute,
    tear_down,
)

OFFSET = 5.0


def configure_dish_leaf_node(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dishln_pointing_device = dev_factory.get_device(DISHLN_POINTING_DEVICE)
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
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )
    track_table_error_before_configure = dish_leaf_node.trackTableErrors
    logger.info(
        "track_table_error_before_configure: %s",
        track_table_error_before_configure,
    )

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )
    group_callback["pointingState"].assert_change_event(
        (PointingState.TRACK),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )

    # Continue track table calculation for some time
    sleep(5)

    # Get the Dish1 device class and server
    db = Database()
    dish1_info = db.get_device_info(DISH_MASTER_DEVICE)
    dish1_dev_class = dish1_info.class_name
    dish1_dev_server = dish1_info.ds_full_name

    # Kill the dish master device
    dish_master_admin = dish_master.adm_name()
    dish_master_admin_proxy = DeviceProxy(dish_master_admin)
    dish1_leaf_admin_dev_name = dish_leaf_node.adm_name()
    dish1_leaf_admin_dev_proxy = DeviceProxy(dish1_leaf_admin_dev_name)

    # delete Dish 1 device from database
    db.delete_device(DISH_MASTER_DEVICE)
    dish_master_admin_proxy.RestartServer()
    # Added a wait for the completion of dish device deletion from TANGO
    # database and the dish device restart
    sleep(5)

    monitor_track_table_errors_attribute(
        dish_leaf_node, track_table_error_before_configure
    )
    track_table_error = dish_leaf_node.trackTableErrors
    logger.info(
        "track_table_error after configure: %s",
        track_table_error,
    )
    expected_message = (
        "Exception while writing tracktable: %sunsupported data_format."
    )
    result = any(expected_message in message for message in track_table_error)
    assert result

    # Add Dish device back to DB
    dev_info = DbDevInfo()
    dev_info.name = DISH_MASTER_DEVICE
    dev_info._class = dish1_dev_class
    dev_info.server = dish1_dev_server
    db.add_device(dev_info)

    dish_master_admin_proxy.RestartServer()
    dish1_leaf_admin_dev_proxy.RestartServer()

    # When device restart it will around 15 sec to up again
    # so wait for the dish1 dishmode attribute to be in ptoper state
    sleep(20)
    dish1_info = db.get_device_info(DISH_MASTER_DEVICE)
    logger.info("dish1_info: %s", dish1_info)

    dish_leaf1_info = db.get_device_info(DISH_LEAF_NODE_DEVICE)
    logger.info("dish_leaf1_info: %s", dish_leaf1_info)

    # delete stale dish leaf node proxy from the dictionary and create new one
    logger.info("dev_factory.dev_proxys: %s", dev_factory.dev_proxys)
    del dev_factory.dev_proxys["ska_mid/tm_leaf_node/d0001"]

    logger.info("dev_factory.dev_proxys: %s", dev_factory.dev_proxys)

    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_leaf_node1 = tango.DeviceProxy("ska_mid/tm_leaf_node/d0001")
    logger.info("State1-----------: %s", dish_leaf_node1.state())
    logger.info("dev_factory.dev_proxys: %s", dev_factory.dev_proxys)
    logger.info("State------------: %s", dish_leaf_node.state())

    result_config, unique_id_config = dish_leaf_node.TrackStop()
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    tear_down(
        dish_leaf_node, dish_master, group_callback, dishln_pointing_device
    )


@pytest.mark.skip(
    reason="Not able to connect to dishLeafNode once it is restarted."
)
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_configure_command(tango_context, group_callback, json_factory):
    configure_dish_leaf_node(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
    )
