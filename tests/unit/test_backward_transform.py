import pytest
from ska_tmc_common import DishHelper

from ska_tmc_dishleafnode import AzElConverter
from tests.settings import DISH_MASTER_DEVICE, create_cm


@pytest.mark.parametrize(
    "timestamp, az, el, expected_ra, expected_dec",
    [
        pytest.param(
            "2019-02-19 06:01:00",
            "0.0079663",
            "-0.5381385",
            "2:31:50.88",
            "89:15:51.4",
        ),
    ],
)
@pytest.mark.skip(reason="Accuracy needs to be fixed")
def test_backward_transform(timestamp, az, el, expected_ra, expected_dec):
    """Test the backward transform method from AzElConverter."""
    cm = create_cm(DISH_MASTER_DEVICE)
    converter = AzElConverter(component_manager=cm)
    converter.create_antenna_obj()
    helper = DishHelper()
    az = float(az)
    el = float(el)
    ra, dec = converter.backward_transform(az, el, timestamp)
    ra = round(ra, 3)
    dec = round(dec, 3)
    ra = helper.degree_to_hour_minute_seconds(ra)
    dec = helper.degree_to_degree_minute_seconds(dec)
    assert expected_ra == ra
    assert expected_dec == dec
