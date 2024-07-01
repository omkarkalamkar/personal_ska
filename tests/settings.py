"""This module provides settings for the test cases."""
import json
import logging
import time
from typing import Final, List

import tango
from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DishMode, PointingState
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DeviceProxy

from ska_tmc_dishleafnode.manager import DishLNComponentManager

configure_logging()

logger = logging.getLogger(__name__)

KVALUE = 9
SLEEP_TIME = 0.5
TIMEOUT = 100

DISH_MASTER_DEVICE = "mid-dish/dish-manager/SKA001"
DISH_LEAF_NODE_DEVICE = "ska_mid/tm_leaf_node/d0001"
SDP_QUEUE_CONNECTOR_DEVICE = "mid-sdp/queueconnector/01"
SDP_QUEUE_CONNECTOR_DEVICE2 = "mid-sdp/queueconnector/02"
COMMAND_COMPLETED = json.dumps([ResultCode.OK, "Command Completed"])

WEATHER_DATA: Final = {
    "temperature": 30.0,
    "pressure": 900.0,
    "humidity": 10,
}


def wait_for_ping(dishleafnode_cm):
    """Method waits for the device ping till timeout specified
    Raises TimeoutError if the device is still unavailable within timeout.
    """
    start_time = time.time()
    elapsed_time = 0
    while dishleafnode_cm._device.ping < 0:
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            raise TimeoutError("Timeout waiting for device ping")


def dish_mode_callback():
    """An empty dishmode callback"""


def pointing_state_callback():
    """An empty pointingstate callback"""


def communication_state_callback():
    """An empty communication_state callback"""


def component_state_callback():
    """An empty component_state callback"""


def pointing_callback():
    """An empty pointing callback"""


def kvalue_validation_callback():
    """An empty kvalue_validation callback"""


def update_availablity_callback():
    """An empty update_availablity callback"""


def update_source_offset_callback():
    """An empty update_source_offset callback"""


def update_last_pointing_data_callback(temp):
    """An empty last pointing data callback"""
    logger.debug(temp)


def create_cm(device: str) -> DishLNComponentManager:
    """Creates component manager for Dish Leaf Node."""
    cm = DishLNComponentManager(
        device,
        logger=logger,
        track_table_entries=25,
        pointing_calculation_period=100,
        _update_dishmode_callback=dish_mode_callback,
        _update_pointingstate_callback=pointing_state_callback,
        communication_state_callback=communication_state_callback,
        component_state_callback=communication_state_callback,
        pointing_callback=pointing_callback,
        kvalue_validation_callback=kvalue_validation_callback,
        _update_availablity_callback=update_availablity_callback,
        _update_source_offset_callback=update_source_offset_callback,
        _update_last_pointing_data_cb=update_last_pointing_data_callback,
    )
    return cm


def get_dishln_command_obj(command_class, cm) -> tuple:
    """Returns component manager and command class object for Dish Leaf Node"""

    adapter_factory = HelperAdapterFactory()
    cm.dish_dev_name = DISH_MASTER_DEVICE
    command_obj = command_class(cm, cm.op_state_model, adapter_factory, logger)
    return cm, command_obj, adapter_factory


def event_remover(group_callback, attributes: List[str]) -> None:
    """Removes residual events from the queue.

    Args:
        group_callback: The group callback object.
        attributes (List[str]): List of attribute names.

    :return: None
    :rtype: None"""
    for attribute in attributes:
        try:
            iterable = group_callback._mock_consumer_group._views[
                attribute
            ]._iterable
            for node in iterable:
                logger.info("Payload is: %s", repr(node.payload))
                node.drop()
        except KeyError:
            pass


def wait_for_device_to_up(device_proxy):
    """This test case waits for the device"""
    timeout = 0
    while timeout < 30:
        time.sleep(1)
        timeout = timeout + 1
        if device_proxy.dishMode == DishMode.STANDBY_LP:
            return True
    return False


def wait_for_dish_mode(
    cm: DishLNComponentManager, dish_mode: DishMode
) -> bool:
    """Waits for dishmode to become given dish mode. Times out if the change
    does not occur. Current timeout is 10s.
    """
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time < TIMEOUT:
        cm.update_device_dish_mode(dish_mode)
        if cm.dishMode == int(dish_mode):
            return True
        elapsed_time = time.time() - start_time
    logger.info("Current Dishmode is %s", cm.dishMode)
    return False


def wait_for_attribute_value(
    device: DeviceProxy, attribute_name: str, value: str = "[]"
) -> bool:
    """Waits for attribute value to change on the given device."""
    start_time = time.time()
    while device.read_attribute(attribute_name).value == value:
        time.sleep(0.5)
        if time.time() - start_time >= TIMEOUT:
            return False
    return True


def wait_for_unresponsive(cm: DishLNComponentManager) -> bool:
    """Waits for device unresponsive update to True.

    :return: True if the device becomes unresponsive within the timeout,
        False otherwise.
    :return: boolean"""
    start_time = time.time()
    elapsed_time = 0
    timeout = 50
    while elapsed_time < timeout:
        if cm.get_device().unresponsive:
            return True
        elapsed_time = time.time() - start_time
    return False


def tear_down(
    dish_leaf_node: DeviceProxy, dish_master: DeviceProxy, group_callback
):
    """Teardown for the Dish Leaf Node device."""
    current_pointing_state = dish_master.pointingState
    if current_pointing_state == PointingState.TRACK:
        result, unique_id = dish_leaf_node.TrackStop()
        assert result[0] == ResultCode.QUEUED

        dish_leaf_node.subscribe_event(
            "longRunningCommandsInQueue",
            tango.EventType.CHANGE_EVENT,
            group_callback["longRunningCommandsInQueue"],
        )
        group_callback["longRunningCommandsInQueue"].assert_change_event(
            ("TrackStop",), lookahead=4
        )

        dish_leaf_node.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            group_callback["longRunningCommandResult"],
        )
        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id[0], str(int(ResultCode.OK))),
            lookahead=4,
        )
    dish_master.SetDirectPointingState(PointingState.NONE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dish_master.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    dish_master.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    group_callback["pointingState"].assert_change_event(
        (PointingState.NONE),
        lookahead=12,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=12,
    )


def build_partial_configure_data(
    partial_config: str,
    offset: float,
) -> List[str]:
    """Build and return the jsons for partial configuration in a list."""
    configurations = []
    partial_config = json.loads(partial_config)

    partial_config["pointing"]["target"]["ca_offset_arcsec"] = offset
    partial_config["pointing"]["target"]["ie_offset_arcsec"] = 0.0
    configurations.append(json.dumps(partial_config))

    partial_config["pointing"]["target"]["ca_offset_arcsec"] = 0.0
    partial_config["pointing"]["target"]["ie_offset_arcsec"] = offset
    configurations.append(json.dumps(partial_config))

    partial_config["pointing"]["target"]["ca_offset_arcsec"] = -offset
    partial_config["pointing"]["target"]["ie_offset_arcsec"] = 0.0
    configurations.append(json.dumps(partial_config))

    partial_config["pointing"]["target"]["ca_offset_arcsec"] = 0.0
    partial_config["pointing"]["target"]["ie_offset_arcsec"] = -offset
    configurations.append(json.dumps(partial_config))

    return configurations


def wait_and_validate_attribute_value_available(
    device: DeviceProxy,
    attribute_name: str,
    expected_value: str,
    timeout: int = 300,
) -> bool:
    """This method wait and validate if attribute value is equal to provided
    expected value

    Args:
        device (DeviceProxy): The Tango DeviceProxy object.
        attribute_name (str): The name of the attribute.
        expected_value (str): The expected value of the attribute.
        timeout (int, optional): Timeout in seconds.

    return: True if attribute value matches the expected value within the
        timeout, False otherwise.
    rtype: bool"""
    count = 0
    error = None
    attribute_value = None
    while count <= timeout:
        try:
            count += 30
            time.sleep(30)
            attribute_value = device.read_attribute(attribute_name).value
            if attribute_value == expected_value:
                return True
            logger.info(
                "%s current %s value: %s",
                device.name(),
                attribute_name,
                attribute_value,
            )
        except Exception as exception:
            # Device gets unavailable due to restart and the above command
            # tries to access the attribute resulting into exception
            # It keeps it printing till the attribute is accessible
            # the exception log is suppressed by storing into variable
            # the error is printed later into the log in case of failure
            error = exception

    logger.exception(
        "Exception occurred while reading attribute %s and count is %s",
        error,
        count,
    )
    return False


def dln_can_communicate_with_dish_master(
    device: DeviceProxy,
):
    """This method tries to check the dish manager is available
    for execution of further commands.

     Args:
        device (DeviceProxy): The DishLN device proxy.

    :return: True if the dish manager is available, False otherwise.
    :rtype: bool: True if the dish manager is available, False otherwise.
    """
    retry = 0
    flag = False
    timeout = 120
    while retry < 3 and not flag:
        count = 0
        error = ""
        while count <= timeout and not flag:
            count += 20
            # observed it dish master takes time to be available and to
            # sync up with
            time.sleep(20)
            try:
                result_code, _ = device.SetKValue(KVALUE)
                if result_code == ResultCode.OK:
                    flag = True
            except Exception as exception:
                # Device gets unavailable due to restart and the above command
                # tries to access the attribute resulting into exception
                # It keeps it printing till the attribute is accessible
                # the exception log is suppressed by storing into variable
                # the error is printed later into the log in case of failure
                error = exception
        retry = retry + 1

    if not flag:
        logging.exception(
            "Exception occurred while reading attribute %s and cnt is %s",
            error,
            count,
        )
    return flag
