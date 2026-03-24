from datetime import datetime
from time import sleep

import pytest
from astropy.time import Time
from astropy.utils import iers
from katpoint import Target

from ska_tmc_dishleafnode.az_el_converter import (
    AzElConverter,
    AzElConverter_v2,
)
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
    """Test RA/Dec → Az/El conversion using the AzElConverter.
    Verifies equatorial to horizon coordinate transformation
    with IERS data."""

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
    "target_name, line1, line2, expected_az, expected_el, timestamp",
    [
        (
            "ISS (ZARYA)",
            "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927",  # noqa: E501
            "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537",  # noqa: E501
            25.388043,
            -6.984832,
            "2022-03-19 18:21:50",
        ),
    ],
)
def test_tle_to_azel_v2(
    target_name: str,
    line1: str,
    line2: str,
    expected_az: float,
    expected_el: float,
    timestamp: str,
    cm_pointing_device,
):
    """Test TLE satellite target → Az/El using AzElConverter_v2.
    Validates Skyfield TLE parsing, antenna observer,
    and refraction."""
    cm = cm_pointing_device
    cm.iers_a = iers.IERS_A.open(IERS_DATA_STORAGE_PATH)

    tle_description = f"{target_name}, tle, {line1}, {line2}"
    target = Target(tle_description)
    target.antenna = cm.observer
    cm.antenna_target = target
    cm.projection_and_fixed_trajectory_data = ["SIN", "azel", 0.0, 0.0]

    converter = AzElConverter_v2(component_manager=cm)
    timestamp_obj = Time(timestamp, scale="utc")
    az, el = converter.point(timestamp_obj)
    az = round(az, 6)
    el = round(el, 6)

    logger.info("Azimuth is: %s", az)
    logger.info("Elevation is: %s", el)

    assert az == expected_az
    assert el == expected_el


def test_azel_converter_v2_supports_projection_and_fixed_offsets(
    cm_pointing_device,
):
    """Test the new AzElConverter_v2.point() implementation (ADR-106) that
    supports projection and fixed trajectory offsets using plane_to_sphere
    conversion for mapping scans."""
    cm = cm_pointing_device

    cm.array_layout = ARRAY_LAYOUT
    cm.fixed_x_offset = 0.0
    cm.fixed_y_offset = 5.0
    cm.projection_name = "SIN"
    cm.projection_alignment = "azel"

    target = Target("dummy_target, radec, 0:00:00, 0:00:00")
    target.antenna = cm.observer
    cm.antenna_target = target

    converter = AzElConverter_v2(component_manager=cm)
    timestamp = Time(datetime.utcnow(), scale="utc")
    az, el = converter.point(timestamp)

    assert isinstance(az, float)
    assert isinstance(el, float)
