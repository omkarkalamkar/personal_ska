import pytest
from ska_tmc_common import DishHelper

from ska_tmc_dishleafnode import AzElConverter
from tests.settings import DISH_MASTER_DEVICE, create_cm


@pytest.mark.parametrize(
    "timestamp, az, el, expected_ra, expected_dec",
    [
        pytest.param(
            "2019-02-19 06:01:00", "0:27:23.1738", "-31:14:17.8667", "02:31:50.88", "89:15:51.4"
        ),
    ],
)
@pytest.mark.skip(reason="The unit conversion methods are yet to be updated.")
def test_backward_transform(timestamp, az, el, expected_ra, expected_dec):
    """Test the backward transform method from AzElConverter."""
    cm = create_cm(DISH_MASTER_DEVICE)
    converter = AzElConverter(component_manager=cm)
    converter.create_antenna_obj()
    helper = DishHelper()
    ra, dec = converter.backward_transform(az, el, timestamp)
    ra = helper.dd_to_dms(ra)
    dec = helper.dd_to_dms(dec)
    assert expected_ra == ra
    assert expected_dec == dec
