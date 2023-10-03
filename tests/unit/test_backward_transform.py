import pytest

from ska_tmc_dishleafnode import AzElConverter
from tests.settings import DISH_MASTER_DEVICE, create_cm


@pytest.mark.parametrize(
    "timestamp, az, el, expected_ra, expected_dec",
    [
        pytest.param(
            "2019-02-19 06:01:00",
            "0.0079663",
            "-0.5381385",
            "2:31:50.9",
            "89:15:51.4",
        ),
        pytest.param(
            "2019-02-19 06:01:00", "5.0134659", "1.3590781", "16:29:24.46", "-26:25:55.7"
        ),
        pytest.param(
            "2022-03-19 09:21:50",
            "3.0284012",
            "-0.7644920",
            "10:14:56.82",
            "-14:44:15.13",
        ),
    ],
)
def test_backward_transform(timestamp, az, el, expected_ra, expected_dec):
    """Test the backward transform method from AzElConverter."""
    cm = create_cm(DISH_MASTER_DEVICE)
    converter = AzElConverter(component_manager=cm)
    converter.create_antenna_obj()
    az = float(az)
    el = float(el)
    ra, dec = converter.backward_transform(az, el, timestamp)
    ra = f"{int(ra[0])}:{abs(int(ra[1]))}:{abs(round(ra[2],2))}"
    dec = f"{int(dec[0])}:{abs(int(dec[1]))}:{abs(round(dec[2],2))}"
    assert expected_ra == ra
    assert expected_dec == dec
