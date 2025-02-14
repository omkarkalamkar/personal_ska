"""This module provides settings for the test cases."""
import json
import logging
import time
from datetime import datetime
from typing import List

import tango
from astropy.time import Time
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
NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES = 150

DISH_MASTER_DEVICE = "mid-dish/dish-manager/SKA001"
DISH_LEAF_NODE_DEVICE = "ska_mid/tm_leaf_node/d0001"
SDP_QUEUE_CONNECTOR_DEVICE = "mid-sdp/queueconnector/01"
SDP_QUEUE_CONNECTOR_DEVICE2 = "mid-sdp/queueconnector/02"
DISHLN_POINTING_DEVICE = "mid-tmc/dish-pointing/d0001"
COMMAND_COMPLETED = json.dumps([ResultCode.OK, "Command Completed"])
COMMAND_FAILED = json.dumps(
    [ResultCode.FAILED, "Exception occured, command failed."]
)
COMMAND_FAILED_WITH_TRACK = json.dumps(
    [
        ResultCode.FAILED,
        "Dish manager did not receive TrackTable. Track() command is not "
        + "invoked on the Dish.",
    ]
)
COMMAND_TIMEOUT = json.dumps(
    [ResultCode.FAILED, "Timeout has occurred, command failed"]
)
COMMAND_CONFIGURE_BAND_TIMEOUT = json.dumps(
    [
        ResultCode.FAILED,
        "Timeout occurred while waiting for "
        + "configuredBand command to be completed in Configure command.",
    ]
)
SKA_EPOCH = "1999-12-31T23:59:28Z"
COMMAND_COMPLETION_MESSAGE = "Command Completed"
# this json is stored remotely so needs to hardcode this here
GPM_JSON = (
    '{"band1pointingmodelparams": "", "band2pointingmodelparams": '
    + '"[-491.0523681640625, -46.494388580322266, -0.20043884217739105, '
    + '6.303488731384277, 0.0, 16.015695571899414, 0.0, 11.97440242767334, '
    + '-3.738542079925537, 0.0, 0.0, 1655.9869384765625, -145.2842254638672, '
    + '-26.760848999023438, 0.0, 0.0, 0.0, 0.0]", "band3pointingmodelparams": '
    + '"", "band4pointingmodelparams": "", "band5apointingmodelparams": "", '
    + '"band5bpointingmodelparams": ""}'
)
NON_SIDEREAL_OBJECTS = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
]


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


def pointing_model_param_callaback():
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


def update_track_table_errors_callback(value):
    """An empty update_track_table_error callback"""
    logger.info("Track Table error is: %s", value)


def update_source_offset_callback(source_offset):
    """An empty update_source_offset callback"""
    logger.info("Source offset is: %s", source_offset)


def update_last_pointing_data_callback(temp):
    """An empty last pointing data callback"""
    logger.debug(temp)


def update_health_state_callback(temp):
    """An empty health state callback"""
    logger.debug(temp)


def create_cm(device: str) -> DishLNComponentManager:
    """Creates component manager for Dish Leaf Node."""
    cm = DishLNComponentManager(
        device,
        logger=logger,
        dishln_pointing_fqdn=DISHLN_POINTING_DEVICE,
        _update_dishmode_callback=dish_mode_callback,
        _update_dish_pointing_model_param=(pointing_model_param_callaback),
        _update_pointingstate_callback=pointing_state_callback,
        communication_state_callback=communication_state_callback,
        component_state_callback=communication_state_callback,
        pointing_callback=pointing_callback,
        kvalue_validation_callback=kvalue_validation_callback,
        _update_availablity_callback=update_availablity_callback,
        _update_source_offset_callback=update_source_offset_callback,
        _update_last_pointing_data_cb=update_last_pointing_data_callback,
        _update_track_table_errors_callback=update_track_table_errors_callback,
        _update_health_state_callback=update_health_state_callback,
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
    count = 0
    timeout = 20
    while count < timeout:
        if cm.get_device().unresponsive:
            return True
        time.sleep(1)
        count += 1
    return False


def tear_down(
    dish_leaf_node: DeviceProxy,
    dish_master: DeviceProxy,
    group_callback,
):
    """Teardown for the Dish Leaf Node device."""

    logger.info("Invoked tear_down")
    current_pointing_state = dish_master.pointingState
    if current_pointing_state == PointingState.TRACK:
        result, unique_id = dish_leaf_node.TrackStop()
        assert result[0] == ResultCode.QUEUED

        lrcr_event_id = dish_leaf_node.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            group_callback["longRunningCommandResult"],
        )
        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id[0], COMMAND_COMPLETED),
            lookahead=4,
        )
        dish_leaf_node.unsubscribe_event(lrcr_event_id)
    dish_master.SetDirectPointingState(PointingState.NONE)
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

    group_callback["pointingState"].assert_change_event(
        (PointingState.NONE),
        lookahead=12,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=12,
    )
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_master.clearcommandcallinfo()


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
            attribute_value = device.read_attribute(attribute_name).value
            if attribute_value == expected_value:
                return True
            logger.info(
                "%s current %s value: %s",
                device.name(),
                attribute_name,
                attribute_value,
            )
            count += 1
            time.sleep(1)
        except Exception as exception:
            # Device gets unavailable due to restart and the above command
            # tries to access the attribute resulting into exception
            # It keeps it printing till the attribute is accessible
            # the exception log is suppressed by storing into variable
            # the error is printed later into the log in case of failure
            error = exception
            count += 1
            time.sleep(1)

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


def simulate_result_code_event(
    cm: DishLNComponentManager,
    command_name: str,
    result: ResultCode,
):
    """Simulate LRCR event from given device for given result."""
    command_id = ""
    device_name = "mid-dish/dish-manager/SKA001"
    command_id = f"{time.time()}_{command_name}"
    cm.command_unique_id_dict[command_name] = command_id
    logging.info("command_id  is: %s", command_id)
    command_result = (
        command_id,
        json.dumps(
            [
                result,
                f"{command_name} completed",
            ]
        ),
    )
    cm.update_device_long_running_command_result(device_name, command_result)


def simulate_track_table_event(
    cm: DishLNComponentManager,
):
    """Simulate an event for tracktable."""
    cm.update_program_track_table(
        [
            775853423.2247269,
            178.758613204265,
            31.165682681453,
        ]
    )


def simulate_dish_mode_event(
    cm: DishLNComponentManager,
    dishmode: DishMode,
):
    """Simulate Dish mode event from dish master."""
    cm.update_device_dish_mode(dishmode)


def get_non_sidereal_json_for_now(non_side_real_json, cm) -> str:
    """Return the json for Configure command with visible non-sidereal object
    according to current time.
    """
    configure_input_json = json.loads(non_side_real_json)
    timestamp: Time = Time(datetime.utcnow(), scale="utc")
    for target in NON_SIDEREAL_OBJECTS:
        _, El = cm.converter.point_to_body(target, timestamp)
        if El > cm.elevation_min_limit:
            configure_input_json["pointing"]["target"]["target_name"] = target
            return json.dumps(configure_input_json)
    return ""


def get_non_sidereal_json_for_source_not_visible(non_side_real_json) -> str:
    """Return the json for Configure command with non-visible non-sidereal
    object according to current time.
    """
    current_time = int(datetime.utcnow().strftime("%H"))
    logging.info("CURRENT TIME: %s", current_time)
    configure_input_json = json.loads(non_side_real_json)

    if 8 <= current_time <= 14:
        configure_input_json["pointing"]["target"]["target_name"] = "Uranus"
        return json.dumps(configure_input_json)
    if 3 <= current_time <= 8:
        configure_input_json["pointing"]["target"]["target_name"] = "Saturn"
        return json.dumps(configure_input_json)
    if current_time <= 3 or current_time >= 21:
        configure_input_json["pointing"]["target"]["target_name"] = "Mars"
        return json.dumps(configure_input_json)
    if 17 <= current_time <= 21:
        configure_input_json["pointing"]["target"]["target_name"] = "Mars"
        return json.dumps(configure_input_json)
    if 14 <= current_time <= 15:
        configure_input_json["pointing"]["target"]["target_name"] = "Mars"
        return json.dumps(configure_input_json)
    return ""


def get_non_sidereal_json_for_source_unknown(non_side_real_json) -> str:
    """Return the json for Configure command with unknown non-sidereal
    object."""
    configure_input_json = json.loads(non_side_real_json)
    configure_input_json["pointing"]["target"]["target_name"] = "Pluto"
    return json.dumps(configure_input_json)


def monitor_track_table_errors_attribute(
    dish_leaf_node, track_table_error_before_configure
) -> bool:
    """Monitors the trackTableErrors attribute and returns True if the
    value is updated"""
    time_consumed = 0
    track_table_errors = dish_leaf_node.trackTableErrors

    while track_table_errors == track_table_error_before_configure:
        track_table_errors = dish_leaf_node.trackTableErrors
        time.sleep(0.5)
        if time_consumed >= TIMEOUT:
            return False
        time_consumed = time_consumed + 0.5
    logger.info("TrackTableErrors: %s", dish_leaf_node.trackTableErrors)
    return True
