import numpy as np
import pytest
from ska_tmc_common import DevFactory

from tests.settings import (
    SDP_QUEUE_CONNECTOR_DEVICE,
    SDP_QUEUE_CONNECTOR_DEVICE2,
)

SDP_QUEUE_CONNECTOR_FQDN = (
    f"{SDP_QUEUE_CONNECTOR_DEVICE}/" "pointing_cal_{dish_id}"
)

POINTING_CAL1 = [1.1, 2.2, 3.3]
POINTING_CAL2 = [3.1, 4.2, 5.3]
POINTING_CAL3 = [5.5, np.NAN, 7.3]
DISH_ID = "ska001"
ATTRIBUTE_NAME = "pointing_cal_ska001"


@pytest.mark.utest
@pytest.mark.repeat(50)
def test_sdpqc_fqdn_info_is_stored(tango_context, cm):
    """This test case checks the received SDP Queue connector
    information getting stored in component manager as expected."""
    dev_name = SDP_QUEUE_CONNECTOR_FQDN.rsplit("/", 1)[0]
    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN, DISH_ID)
    assert dev_name == cm.queue_connector_device_info.dev_name
    assert ATTRIBUTE_NAME == cm.queue_connector_device_info.attribute_name
    assert cm.queue_connector_device_info.subscribed_to_attribute


@pytest.mark.utest
@pytest.mark.repeat(50)
def test_dish_leaf_node_gets_the_pointing_cal(tango_context, cm):
    """This test case verifies the dish leaf node gets the
    SDP pointing calibration data from SDP Queue connector device."""
    sdp_queue_connector = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    dev_name = SDP_QUEUE_CONNECTOR_FQDN.rsplit("/", 1)[0]
    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN, DISH_ID)
    assert dev_name == cm.queue_connector_device_info.dev_name
    assert ATTRIBUTE_NAME == cm.queue_connector_device_info.attribute_name
    assert cm.queue_connector_device_info.subscribed_to_attribute
    sdp_queue_connector.SetPointingCalSka001(POINTING_CAL1)
    assert np.array_equal(
        POINTING_CAL1, list(cm.queue_connector_device_info.pointing_data)
    )
    assert np.array_equal(
        POINTING_CAL1, list(cm.received_pointing_data)[0].pointing_data
    )
    assert np.array_equal(POINTING_CAL1, list(cm.last_pointing_data))


@pytest.mark.utest
@pytest.mark.repeat(50)
def test_with_updated_sdpqc_fqdn(tango_context, cm):
    """This test case verifies dish leaf node is subscribed
    to only one SDP queuconnector device in given observation.
    Dish leaf node unsubscibes the old sdp queue connector"""
    sdp_queue_connector1 = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    sdp_queue_connector2 = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE2)
    dev_name = SDP_QUEUE_CONNECTOR_FQDN.rsplit("/", 1)[0]
    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN, DISH_ID)
    assert dev_name == cm.queue_connector_device_info.dev_name
    SDP_QUEUE_CONNECTOR_FQDN2 = (
        f"{SDP_QUEUE_CONNECTOR_DEVICE2}/" "pointing_cal_{dish_id}"
    )
    dev_name = SDP_QUEUE_CONNECTOR_FQDN2.rsplit("/", 1)[0]
    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN2, DISH_ID)
    assert dev_name == cm.queue_connector_device_info.dev_name
    assert ATTRIBUTE_NAME == cm.queue_connector_device_info.attribute_name
    assert cm.queue_connector_device_info.subscribed_to_attribute
    cm.queue_connector_device_info.subscribed_to_attribute = True
    sdp_queue_connector2.SetPointingCalSka001(POINTING_CAL2)
    sdp_queue_connector1.SetPointingCalSka001(POINTING_CAL1)
    assert np.array_equal(
        POINTING_CAL2, list(cm.queue_connector_device_info.pointing_data)
    )
    assert np.array_equal(
        POINTING_CAL2, list(cm.received_pointing_data)[0].pointing_data
    )
    assert np.array_equal(POINTING_CAL2, list(cm.last_pointing_data))


@pytest.mark.utest
@pytest.mark.repeat(50)
def test_to_check_nan_received_from_sdp_not_processed(tango_context, cm):
    """This test case verifies the dish leaf node gets the
    SDP pointing calibration data from SDP Queue connector device."""
    cm.process_sqpqc_attribute_fqdn(SDP_QUEUE_CONNECTOR_FQDN, DISH_ID)
    sdp_queue_connector = DevFactory().get_device(SDP_QUEUE_CONNECTOR_DEVICE)
    sdp_queue_connector.SetPointingCalSka001(POINTING_CAL3)
    dev_name = SDP_QUEUE_CONNECTOR_FQDN.rsplit("/", 1)[0]
    assert dev_name == cm.queue_connector_device_info.dev_name
    assert ATTRIBUTE_NAME == cm.queue_connector_device_info.attribute_name
    assert not np.isnan(cm.queue_connector_device_info.pointing_data).any()
    # Verify NaN list is not processed by DLN
    assert not np.isnan(list(cm.received_pointing_data)[0].pointing_data).any()
    assert not np.isnan(cm.queue_connector_device_info.pointing_data).any()
    assert np.isnan(cm.last_pointing_data).any()


@pytest.mark.utest
@pytest.mark.repeat(50)
@pytest.mark.parametrize(
    "invalid_list", [[1.1], [1], [2.2, 2], [3.3, 4.4, 5.5, 6.6], [], [""]]
)
def test_invalid_list(cm_without_er_lp, invalid_list):
    """Test to verify invalid list"""
    cm = cm_without_er_lp
    with pytest.raises(ValueError):
        cm.validate_float_list(invalid_list, number_of_values=3)
