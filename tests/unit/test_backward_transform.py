import pytest

from ska_tmc_dishleafnode import AzElConverter
from tests.settings import DISH_MASTER_DEVICE, WEATHER_DATA, create_cm


@pytest.mark.parametrize(
    "timestamp, az, el, expected_ra, expected_dec",
    [
        (
            "2019-02-19 06:01:00",
            "0.4564362",
            "-30.8330656",
            "2:31:50.9",
            "89:15:51.4",
        ),
        ("2019-02-19 06:01:00", "287.2504396", "77.8694392", "16:29:24.46", "-26:25:55.7"),
        (
            "2022-03-19 09:21:50",
            "173.5146073",
            "-43.8021646",
            "10:14:56.82",
            "-14:44:15.13",
        ),
    ],
)
def test_azel_to_radec(timestamp, az, el, expected_ra, expected_dec, tango_context):
    """Test the backward transform method from AzElConverter."""
    cm = create_cm(DISH_MASTER_DEVICE)
    converter = AzElConverter(component_manager=cm)
    converter.create_antenna_obj()
    ra, dec = converter.azel_to_radec(az, el, timestamp, WEATHER_DATA)
    assert expected_ra == ra
    assert expected_dec == dec
