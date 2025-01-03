import json
from time import sleep

import pytest
import tango
from numpy import NaN, isnan
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory, DishMode, PointingState
from tango import AttrQuality

from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    DISHLN_POINTING_DEVICE,
    SDP_QUEUE_CONNECTOR_DEVICE,
    tear_down,
)

POINTING_CAL_NAN = [3.1, NaN, 5.3]
POINTING_CAL_RESET = [1.1, 0.0, 0.0]
EXTEND_MILLISECONDS = 100
TIMEOUT = 10


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_sdpqc_nan_functionality(tango_context, json_factory, group_callback):
    """This test tests the NaN received from SDPQC functionality"""
    sdp_queue_connector = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    dish_master = DevFactory().get_device(DISH_MASTER_DEVICE)
    dishln_pointing_device = DevFactory().get_device(DISHLN_POINTING_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    device_host = tango.Database().get_db_host()
    device_port = tango.Database().get_db_port()
    SDPQC_FQDN = (
        f"{device_host}:{device_port}/"
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/"
        "pointing_cal_{dish_id}"
    )
    dish_leaf_node.sdpQueueConnectorFqdn = SDPQC_FQDN
    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
        stateless=True,
    )
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
    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=4,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )

    configure_input_str = json_factory("dishleafnode_configure")
    load_conf = json.loads(configure_input_str)
    load_conf["pointing"]["correction"] = "UPDATE"
    configure_input_str = json.dumps(load_conf)

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    dish_leaf_node.unsubscribe_event(lrcr_event_id)

    # # Assert TrackLoadStaticOff command not invoked when NaN
    # # received in pointing cal
    with pytest.raises(AssertionError):
        lrcr_event_id = dish_master.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            group_callback["longRunningCommandResult"],
            stateless=True,
        )
        sdp_queue_connector.SetPointingCalSka001(POINTING_CAL_NAN)
        unique_id, _ = group_callback[
            "longRunningCommandResult"
        ].assert_change_event(
            (Anything, COMMAND_COMPLETED),
            lookahead=6,
        )[
            "attribute_value"
        ]
        assert "TrackLoadStaticOff" in unique_id
    assert isnan(json.loads(dish_leaf_node.lastPointingData)).any()
    assert (
        dish_leaf_node.read_attribute("lastPointingData").quality
        == AttrQuality.ATTR_ALARM
    )
    dish_master.unsubscribe_event(lrcr_event_id)

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
        stateless=True,
    )

    # Reset pointing offsets
    sdp_queue_connector.SetPointingCalSka001(POINTING_CAL_RESET)
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

    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    tear_down(
        dish_leaf_node, dish_master, group_callback, dishln_pointing_device
    )
