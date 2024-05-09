from time import sleep

import pytest

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from tests.settings import WEATHER_DATA, logger



@pytest.mark.parametrize(
    "ra, dec, timestamp, expected_az, expected_el",
    [
        # The below parameterized value is unstable.
        # ("16:29:24.46", "-26:25:55.7", "2019-02-19 06:01:00",
        # 287.2504396, 77.8694392),
        (
            "2:31:50.9",
            "89:15:51.4",
            "2019-02-19 06:01:00",
            0.4564362,
            -30.8330656,
        ),
        (
            "10:14:56.82",
            "-14:44:15.13",
            "2022-03-19 09:21:50",
            173.5146073,
            -43.8021646,
        ),
    ],
)
def test_radec_to_azel(
    ra: str,
    dec: str,
    timestamp: str,
    expected_az: float,
    expected_el: float,
    tango_context,
    cm,
    iers_data,
):
    """Function to test AzEl conversion"""
    cm.iers_a = iers_data
    converter = AzElConverter(component_manager=cm)
    retry = 0
    while retry <= 3:
        try:
            converter.create_antenna_obj()
            break
        except Exception as e:
            logger.exception(
                "Exception occurred while creating antenna object: %s", e
            )
            if retry == 2:
                pytest.fail(f"{e}")
            retry += 1
        sleep(0.1)
    az, el = converter.radec_to_azel(ra, dec, timestamp, WEATHER_DATA)
    az = round(az, 7)
    el = round(el, 7)
    assert az == expected_az
    assert el == expected_el
