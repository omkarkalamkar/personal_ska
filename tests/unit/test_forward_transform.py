from time import sleep

import pytest
from astropy.utils import iers

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.constants import IERS_DATA_STORAGE_PATH
from tests.settings import logger


@pytest.mark.parametrize(
    "ra, dec, timestamp, expected_az, expected_el",
    [
        (
            "10:14:56.82",
            "14:44:15.13",
            "2022-03-19 18:21:50",
            46.110779,
            30.663122,
        ),
        (
            "18:36:56.34",
            "38:47:01.3",
            "2019-02-19 06:01:00",
            15.332458,
            18.362424,
        ),
    ],
)
def test_radec_to_azel(
    ra: str,
    dec: str,
    timestamp: str,
    expected_az: float,
    expected_el: float,
    cm,
):
    """Function to test AzEl conversion"""
    cm.get_device().update_unresponsive(False, "")
    cm.iers_a = iers.IERS_A.open(IERS_DATA_STORAGE_PATH)
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
    az = round(az, 6)
    el = round(el, 6)
    logger.info("Azimuth is: %s", az)
    logger.info("Elevation is: %s", el)
    assert az == expected_az
    assert el == expected_el
