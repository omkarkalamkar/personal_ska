from time import sleep

import pytest
from astropy.utils import iers

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.constants import IERS_DATA_STORAGE_PATH
from tests.settings import ARRAY_LAYOUT, logger


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
    cm_without_er_lp,
):
    """Function to test AzEl conversion"""
    cm = cm_without_er_lp
    cm.array_layout = ARRAY_LAYOUT
    cm.get_device(cm.dish_dev_name).update_unresponsive(False, "")
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


@pytest.mark.parametrize(
    "line1, line2, timestamp, target_name, expected_az, expected_el",
    [
        (
            "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927",  # noqa: E501
            "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537",  # noqa: E501
            "2025-03-17 12:00:00",
            "ISS_TLE",
            238.445387,
            -38.336494,
        ),
    ],
)
def test_tle_to_azel(
    line1: str,
    line2: str,
    timestamp: str,
    target_name: str,
    expected_az: float,
    expected_el: float,
    cm_without_er_lp,
):
    """Test to check TLE to AzEl conversion"""
    cm = cm_without_er_lp
    cm.array_layout = ARRAY_LAYOUT
    cm.get_device(cm.dish_dev_name).update_unresponsive(False, "")
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

    az_el = converter.tle_to_azel(
        line1, line2, timestamp, target_name=target_name
    )

    assert isinstance(az_el, list)
    assert len(az_el) == 2

    az, el = az_el
    az = round(az, 6)
    el = round(el, 6)

    logger.info(
        f"[{target_name}] Computed Az = {az}, Expected = {expected_az}"
    )
    logger.info(
        f"[{target_name}] Computed El = {el}, Expected = {expected_el}"
    )

    assert az == expected_az
    assert el == expected_el
