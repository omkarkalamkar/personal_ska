import datetime
import json
import time

import pytest
import tango
from numpy import NaN, array_equal, isnan
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory
from tango import AttrQuality

from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    SDP_QUEUE_CONNECTOR_DEVICE,
)

POINTING_CAL = [1.1, 1.1, 1.2]
POINTING_CAL_NAN = [3.1, NaN, 5.3]
POINTING_CAL_RESET = [1.1, 0.0, 0.0]
EXTEND_MILLISECONDS = 100
TIMESTAMP_RA_DEC = ["2019-02-19 06:01:00", "16:29:24.46", "-26:25:55.7"]
TIMEOUT = 10


def utc_timestamp(timestamp: str) -> float:
    """Method to return  timestamp in float for given date"""
    timestamp_str = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    dt_utc = timestamp_str.replace(tzinfo=datetime.timezone.utc)
    extended_time = dt_utc + datetime.timedelta(
        milliseconds=EXTEND_MILLISECONDS
    )
    utc_timestamp = extended_time.timestamp() * 1000
    return utc_timestamp


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_sdpqc_functionality(tango_context, group_callback):
    sdp_queue_connector = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    dish_master = DevFactory().get_device(DISH_MASTER_DEVICE)
    device_host = tango.Database().get_db_host()
    device_port = tango.Database().get_db_port()
    SDPQC_FQDN = (
        f"{device_host}:{device_port}/"
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/"
        "pointing_cal_{dish_id}"
    )
    dish_leaf_node.sdpQueueConnectorFqdn = SDPQC_FQDN
    dish_master.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandStatus"],
        stateless=True,
    )
    # Raise event on SDP Queue connector attribute
    sdp_queue_connector.SetPointingCalSka001(POINTING_CAL)
    # Assert TrackLoadStaticOff command gets executed on reception of
    # event from SDP queue connector attribute.
    unique_id, message = group_callback[
        "longRunningCommandStatus"
    ].assert_change_event(
        (Anything, "COMPLETED"),
        lookahead=10,
    )[
        "attribute_value"
    ]
    assert "TrackLoadStaticOff" in unique_id
    assert "COMPLETED" in message
    assert array_equal(
        json.loads(dish_leaf_node.lastPointingData), POINTING_CAL
    )

    # Verify actual pointing affected with pointing calibration data
    dish_master.programTrackTable = [
        utc_timestamp("2019-02-19 06:01:00"),
        287.2504396,
        77.8694392,
    ]
    elapsed_time = 0
    flag = True
    while flag and elapsed_time < TIMEOUT:
        if "2019" in json.loads(dish_leaf_node.actualpointing)[0]:
            flag = False
            break
        elapsed_time = elapsed_time + 1
        time.sleep(1)
    assert not flag
    received_actual_pointing = json.loads(dish_leaf_node.actualpointing)
    assert TIMESTAMP_RA_DEC[0] == received_actual_pointing[0]
    assert TIMESTAMP_RA_DEC[1] != received_actual_pointing[1]
    assert TIMESTAMP_RA_DEC[2] != received_actual_pointing[2]

    # # Assert TrackLoadStaticOff command not invoked when NaN
    # # received in pointing cal
    with pytest.raises(AssertionError):
        sdp_queue_connector.SetPointingCalSka001(POINTING_CAL_NAN)
        unique_id, _ = group_callback[
            "longRunningCommandStatus"
        ].assert_change_event(
            (Anything, "COMPLETED"),
            lookahead=6,
        )[
            "attribute_value"
        ]
        assert "TrackLoadStaticOff" not in unique_id
    assert isnan(json.loads(dish_leaf_node.lastPointingData)).any()
    assert (
        dish_leaf_node.read_attribute("lastPointingData").quality
        == AttrQuality.ATTR_ALARM
    )
    # Change actual pointing timestamp
    dish_master.programTrackTable = [
        utc_timestamp("2024-02-19 06:01:00"),
        11.2504396,
        33.8694392,
    ]
    # Reset pointing offsets
    sdp_queue_connector.SetPointingCalSka001(POINTING_CAL_RESET)
