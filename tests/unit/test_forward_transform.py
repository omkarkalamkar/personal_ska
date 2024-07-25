from time import sleep

import pytest

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from tests.settings import logger


@pytest.mark.parametrize(
    "ra, dec, timestamp, expected_az, expected_el",
    [
        (
            "15:31:50.9",
            "10:15:51.4",
            "2019-02-19 06:01:00",
            322.8709277,
            41.3703589,
        ),
        (
            "10:14:56.82",
            "14:44:15.13",
            "2022-03-19 18:21:50",
            46.110779,
            30.6631224,
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
):
    """Function to test AzEl conversion"""
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
    az, el = converter.radec_to_azel(ra, dec, timestamp)
    az = round(az, 7)
    el = round(el, 7)
    logger.info("Azimuth is: %s", az)
    logger.info("Elevation is: %s", el)
    assert az == expected_az
    assert el == expected_el
