import numpy as np
from ska_tmc_common import DevFactory

from tests.settings import (
    SDP_QUEUE_CONNECTOR_DEVICE,
    SDP_QUEUE_CONNECTOR_DEVICE2,
)

POINTING_CAL1 = [1.1, 2.2, 3.3]
POINTING_CAL2 = [3.1, 4.2, 5.3]


def test_sdpqc_fqdn_info_is_stored(tango_context, cm):
    """This test case checks the received SDP Queue connector
    information getting stored in component manager as expected."""
    SDP_QUEUE_CONNECTOR_FQDN = (
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/pointing_cal_SKA001"
    )
    dev_name = SDP_QUEUE_CONNECTOR_FQDN.rsplit("/", 1)[0]
    dish_id = "ska001"
    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN, dish_id)
    assert dev_name == cm.queue_connector_device_info.dev_name


def test_dish_leaf_node_gets_the_pointing_cal(tango_context, cm):
    """This test case verifies the dish leaf node gets the
    SDP pointing calibration data from SDP Queue connector device."""
    sdp_queue_connector = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    SDP_QUEUE_CONNECTOR_FQDN = (
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/pointing_cal_SKA001"
    )
    dev_name = SDP_QUEUE_CONNECTOR_FQDN.rsplit("/", 1)[0]
    dish_id = "ska001"
    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN, dish_id)
    assert dev_name == cm.queue_connector_device_info.dev_name
    sdp_queue_connector.SetPointingCalSka001(POINTING_CAL1)
    assert np.array_equal(
        POINTING_CAL1, list(cm.sdpqc_pointing_data)[0].pointing_data
    )


def test_with_updated_sdpqc_fqdn(tango_context, cm):
    """This test case verifies dish leaf node is subscribed
    to only one SDP queuconnector device in given observation.
    Dish leaf node unsubscibes the old sdp queue connector"""
    sdp_queue_connector1 = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    sdp_queue_connector2 = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE2)
    SDP_QUEUE_CONNECTOR_FQDN = (
        f"{SDP_QUEUE_CONNECTOR_DEVICE}/pointing_cal_SKA001"
    )
    dev_name = SDP_QUEUE_CONNECTOR_FQDN.rsplit("/", 1)[0]
    dish_id = "ska001"
    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN, dish_id)
    assert dev_name == cm.queue_connector_device_info.dev_name
    SDP_QUEUE_CONNECTOR_FQDN2 = (
        f"{SDP_QUEUE_CONNECTOR_DEVICE2}/pointing_cal_SKA001"
    )
    dev_name = SDP_QUEUE_CONNECTOR_FQDN2.rsplit("/", 1)[0]
    dish_id = "ska001"
    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN2, dish_id)
    assert dev_name == cm.queue_connector_device_info.dev_name
    sdp_queue_connector2.SetPointingCalSka001(POINTING_CAL2)
    sdp_queue_connector1.SetPointingCalSka001(POINTING_CAL1)
    assert np.array_equal(
        POINTING_CAL2, list(cm.sdpqc_pointing_data)[0].pointing_data
    )
