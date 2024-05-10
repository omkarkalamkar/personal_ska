from time import sleep

import numpy as np
import pytest
from ska_tmc_common import DevFactory

from tests.settings import (
    SDP_QUEUE_CONNECTOR_DEVICE,
    SDP_QUEUE_CONNECTOR_DEVICE2,
)

POINTING_CAL1 = [1.1, 2.2, 3.3]
POINTING_CAL2 = [3.1, 4.2, 5.3]
POINTING_CAL3 = [5.5, np.NAN, 7.3]


def wait_for_device_event(device_proxy, attribute_value):
    """Method to check value reached to the attribute"""
    timeout = 0
    while timeout < 20:
        if np.array_equal(device_proxy.pointing_cal_ska001, attribute_value):
            break
        timeout = timeout + 1
        sleep(1)

    if timeout >= 20:
        return False
    return True


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
    assert wait_for_device_event(sdp_queue_connector, POINTING_CAL1)
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
    assert wait_for_device_event(sdp_queue_connector2, POINTING_CAL2)
    sdp_queue_connector1.SetPointingCalSka001(POINTING_CAL1)
    assert wait_for_device_event(sdp_queue_connector1, POINTING_CAL1)
    assert np.array_equal(
        POINTING_CAL2, list(cm.sdpqc_pointing_data)[0].pointing_data
    )


def test_to_check_nan_received_from_sdp_not_processed(tango_context, cm):
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
    assert not np.isnan(cm.queue_connector_device_info.pointing_data).any()
    sdp_queue_connector.SetPointingCalSka001(POINTING_CAL3)
    # Verify NaN list is not processed by DLN
    assert not np.isnan(cm.queue_connector_device_info.pointing_data).any()


@pytest.mark.parametrize(
    "invalid_list", [[1.1], [1], [2.2, 2], [3.3, 4.4, 5.5, 6.6], [], [""]]
)
@pytest.mark.utest
@pytest.mark.repeat(20)
def test_invalid_list(cm_without_er_lp, invalid_list):
    """Test to verify invalid list"""
    cm = cm_without_er_lp
    with pytest.raises(ValueError):
        cm.validate_float_list(invalid_list, number_of_values=3)
