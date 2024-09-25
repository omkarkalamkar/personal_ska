import json
from time import sleep

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory, DishMode, PointingState

from ska_tmc_dishleafnode.constants import RESET_OFFSETS
from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    SDP_QUEUE_CONNECTOR_DEVICE,
    logger,
    tear_down,
)

POINTING_CAL = [1.1, 1.1, 1.2]
POINTING_CAL_RESET = [1.1, 0.0, 0.0]


def validate_trackloadstaticoff_invoked(dish_master, group_callback):
    """Method to check TrackLoadStaticOff invoked"""
    LRCR_ID = dish_master.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    count = 0
    timeout = 20
    unique_id = ""
    message = ""
    while "TrackLoadStaticOff" not in unique_id and count < timeout:
        unique_id, message = group_callback[
            "longRunningCommandResult"
        ].assert_change_event(
            (Anything, COMMAND_COMPLETED),
            lookahead=10,
        )[
            "attribute_value"
        ]
        count = count + 1
        sleep(1)
    try:
        assert "Command Completed" in message
        dish_master.unsubscribe_event(LRCR_ID)
    except Exception as e:
        logger.exception("Exception occurred: %s", e)
        assert 0  # To abort the test execution


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize("correction_key", ["UPDATE", "RESET"])
def test_main_config_with_correction_key_update_reset(
    tango_context, json_factory, group_callback, correction_key
):
    """Test to check main configure with
    update and reset correction key
    """
    sdp_queue_connector = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    dish_master = DevFactory().get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    device_host = tango.Database().get_db_host()
    device_port = tango.Database().get_db_port()
    SDPQC_FQDN = (
        f"{device_host}:{device_port}/"
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/"
        "pointing_cal_{dish_id}"
    )
    DISHMODE_ID = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    POINTINGSTATE_ID = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    SOURCE_OFFSET_ID = dish_leaf_node.subscribe_event(
        "sourceOffset",
        tango.EventType.CHANGE_EVENT,
        group_callback["sourceOffset"],
    )
    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )
    dish_leaf_node.sdpQueueConnectorFqdn = SDPQC_FQDN
    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )

    configure_input_str = json_factory("dishleafnode_configure")
    load_conf = json.loads(configure_input_str)
    load_conf["pointing"]["correction"] = correction_key
    configure_input_str = json.dumps(load_conf)

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED
    dish_leaf_node.unsubscribe_event(LRCR_ID)
    if correction_key == "RESET":
        validate_trackloadstaticoff_invoked(dish_master, group_callback)
        command_info_data = dish_master.commandCallInfo
        assert ("TrackLoadStaticOff", "[0. 0.]") in command_info_data
    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    if correction_key == "UPDATE":
        dish_leaf_node.unsubscribe_event(LRCR_ID)
        sdp_queue_connector.SetPointingCalSka001(POINTING_CAL)
        validate_trackloadstaticoff_invoked(dish_master, group_callback)
        command_info_data = dish_master.commandCallInfo
        assert ("TrackLoadStaticOff", "[1.1 1.2]") in command_info_data
        LRCR_ID = dish_leaf_node.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            group_callback["longRunningCommandResult"],
        )

    dish_leaf_node.unsubscribe_event(SOURCE_OFFSET_ID)
    dish_leaf_node.unsubscribe_event(DISHMODE_ID)
    dish_leaf_node.unsubscribe_event(POINTINGSTATE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)

    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize("correction_key", ["UPDATE", "RESET"])
def test_partial_configure_with_update_reset_correction_key(
    tango_context,
    group_callback,
    json_factory,
    correction_key,
):
    """Test for partial config with correction key
    as update and reset"""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    sdp_queue_connector = dev_factory.get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    device_host = tango.Database().get_db_host()
    device_port = tango.Database().get_db_port()
    SDPQC_FQDN = (
        f"{device_host}:{device_port}/"
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/"
        "pointing_cal_{dish_id}"
    )
    dish_leaf_node.sdpQueueConnectorFqdn = SDPQC_FQDN
    DISHMODE_ID = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    POINTINGSTATE_ID = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    SOURCE_OFFSET_ID = dish_leaf_node.subscribe_event(
        "sourceOffset",
        tango.EventType.CHANGE_EVENT,
        group_callback["sourceOffset"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )
    configure_input_str = json_factory("dishleafnode_configure")

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )
    partial_configure_input_str = json_factory("partial_configure")
    load_conf = json.loads(partial_configure_input_str)
    load_conf["pointing"]["correction"] = correction_key
    partial_configure_input_str = json.dumps(load_conf)

    result_config, unique_id_config = dish_leaf_node.Configure(
        partial_configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED
    load_conf = json.loads(partial_configure_input_str)

    # Assert change event is occuring and values are reflecting
    # on sourceOffset attribute.
    if correction_key == "RESET":
        validate_trackloadstaticoff_invoked(dish_master, group_callback)
        command_info_data = dish_master.commandCallInfo
        assert ("TrackLoadStaticOff", "[0. 0.]") in command_info_data
        group_callback["sourceOffset"].assert_change_event(
            RESET_OFFSETS,
            lookahead=2,
        )
    else:
        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id_config[0], COMMAND_COMPLETED),
            lookahead=8,
        )
        dish_leaf_node.unsubscribe_event(LRCR_ID)
        sdp_queue_connector.SetPointingCalSka001(POINTING_CAL)
        validate_trackloadstaticoff_invoked(dish_master, group_callback)
        command_info_data = dish_master.commandCallInfo
        assert ("TrackLoadStaticOff", "[1.1 1.2]") in command_info_data

    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    result_trackstop, unique_id_trackstop = dish_leaf_node.TrackStop()
    assert result_trackstop[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_trackstop[0], COMMAND_COMPLETED),
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

    dish_leaf_node.unsubscribe_event(SOURCE_OFFSET_ID)
    dish_leaf_node.unsubscribe_event(DISHMODE_ID)
    dish_leaf_node.unsubscribe_event(POINTINGSTATE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)
    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize("correction_key", ["", "MAINTAIN"])
def test_configure_with_maintain_notset_correction_key(
    tango_context,
    group_callback,
    json_factory,
    correction_key,
):
    """Test applicable for main config/partial config
    with correction key as not set and maintain"""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    sdp_queue_connector = dev_factory.get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    device_host = tango.Database().get_db_host()
    device_port = tango.Database().get_db_port()
    SDPQC_FQDN = (
        f"{device_host}:{device_port}/"
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/"
        "pointing_cal_{dish_id}"
    )
    dish_leaf_node.sdpQueueConnectorFqdn = SDPQC_FQDN
    DISHMODE_ID = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    POINTINGSTATE_ID = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    SOURCE_OFFSET_ID = dish_leaf_node.subscribe_event(
        "sourceOffset",
        tango.EventType.CHANGE_EVENT,
        group_callback["sourceOffset"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )
    configure_input_str = json_factory("dishleafnode_configure")
    load_conf = json.loads(configure_input_str)
    load_conf["pointing"]["correction"] = correction_key
    configure_input_str = json.dumps(load_conf)

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )
    dish_leaf_node.unsubscribe_event(LRCR_ID)

    # Assert that no TrackLoadStaticOff invoked
    with pytest.raises(AssertionError):
        LRCR_ID = dish_master.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            group_callback["longRunningCommandResult"],
            stateless=True,
        )
        sdp_queue_connector.SetPointingCalSka001(POINTING_CAL)
        unique_id, _ = group_callback[
            "longRunningCommandResult"
        ].assert_change_event(
            (Anything, COMMAND_COMPLETED),
            lookahead=6,
        )[
            "attribute_value"
        ]
        assert "TrackLoadStaticOff" in unique_id
        dish_master.unsubscribe_event(LRCR_ID)

    LRCR_ID = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    result_trackstop, unique_id_trackstop = dish_leaf_node.TrackStop()
    assert result_trackstop[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_trackstop[0], COMMAND_COMPLETED),
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

    dish_leaf_node.unsubscribe_event(SOURCE_OFFSET_ID)
    dish_leaf_node.unsubscribe_event(DISHMODE_ID)
    dish_leaf_node.unsubscribe_event(POINTINGSTATE_ID)
    dish_leaf_node.unsubscribe_event(LRCR_ID)
    tear_down(dish_leaf_node, dish_master, group_callback)
