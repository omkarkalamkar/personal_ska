import tango
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory
import pytest
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    SDP_QUEUE_CONNECTOR_DEVICE,
)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_sdpqc_functionality(tango_context, group_callback):
    sdp_queue_connector = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    dish_leaf_node = DevFactory().get_device(DISH_LEAF_NODE_DEVICE)
    device_host = tango.Database().get_db_host()
    device_port = tango.Database().get_db_port()
    FQDN = f"{device_host}:{device_port}/{SDP_QUEUE_CONNECTOR_DEVICE}"
    SDPQC_FQDN = f"tango://{FQDN}/pointing_cal_SKA001"
    dish_leaf_node.sdpQueueConnectorFqdn = SDPQC_FQDN
    dish_master = DevFactory().get_device(DISH_MASTER_DEVICE)
    dish_master.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandStatus"],
        stateless=True,
    )

    # Raise event on SDP Queue connector attribute
    sdp_queue_connector.SetPointingCalSka001([1.1, 2.2, 3.3])

    # Assert TrackLoadStaticOff command gets executed on reception of
    # event from SDP queue connector attribute.
    unique_id, message = group_callback[
        "longRunningCommandStatus"
    ].assert_change_event(
        (Anything, "COMPLETED"),
        lookahead=6,
    )[
        "attribute_value"
    ]

    assert "TrackLoadStaticOff" in unique_id
    assert "COMPLETED" in message

    sdp_queue_connector.SetPointingCalSka001([3.1, 4.2, 5.3])
    unique_id, message = group_callback[
        "longRunningCommandStatus"
    ].assert_change_event(
        (Anything, "COMPLETED"),
        lookahead=6,
    )[
        "attribute_value"
    ]

    assert "TrackLoadStaticOff" in unique_id
    assert "COMPLETED" in message
