import time
from copy import deepcopy

import pytest
from astropy.time import Time
from ska_tmc_common.v3.dish_utils import DishHelper

from ska_tmc_dishleafnode import AzElConverter
from tests.settings import ARRAY_LAYOUT, SKA_EPOCH, logger


@pytest.mark.parametrize(
    "timestamp, az, el, expected_ra, expected_dec",
    [
        (
            "2019-02-19 06:01:00",
            "322.8709276",
            "41.3703589",
            "15:31:50.9",
            "10:15:51.4",
        ),
        (
            "2022-03-19 18:21:50",
            "46.110779",
            "30.6631224",
            "10:14:56.82",
            "14:44:15.13",
        ),
    ],
)
def test_azel_to_radec(
    timestamp,
    az,
    el,
    expected_ra,
    expected_dec,
    cm_without_er_lp,
):
    """Test the backward transform method from AzElConverter."""
    cm = cm_without_er_lp
    cm.array_layout = ARRAY_LAYOUT
    dish_helper = DishHelper(antenna_data=ARRAY_LAYOUT)
    cm.observer = dish_helper.get_dish_antenna()
    converter = AzElConverter(component_manager=cm)
    converter.dish_helper = dish_helper
    converter.create_antenna_obj()
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
        time.sleep(0.1)
    ra, dec = converter.azel_to_radec(az, el, timestamp)
    assert expected_ra == ra
    assert expected_dec == dec


def test_actual_pointing(cm_without_er_lp):
    """Test to check actual pointing is getting updated"""
    cm = cm_without_er_lp
    cm.array_layout = ARRAY_LAYOUT
    timestamp_str = "2019-02-19 06:01:00"
    epoch_time = Time(SKA_EPOCH, format="isot", scale="utc")
    timestamp_time = Time(timestamp_str, format="iso", scale="utc")
    ska_epoch_tai_timestamp = (timestamp_time - epoch_time).sec
    converter = AzElConverter(component_manager=cm)
    converter.create_antenna_obj()
    cm.perform_reverse_transform(
        [ska_epoch_tai_timestamp, 322.8709276, 41.3703589]
    )

    assert list(cm.actual_pointing) == [
        "2019-02-19 06:01:00",
        "15:31:50.9",
        "10:15:51.4",
    ]


def test_actual_pointing_matches_expected_strings_after_site_shift(
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    cm.array_layout = ARRAY_LAYOUT

    timestamp_str = "2019-02-19 06:01:00"
    epoch_time = Time(SKA_EPOCH, format="isot", scale="utc")
    timestamp_time = Time(timestamp_str, format="iso", scale="utc")
    ska_epoch_tai_timestamp = (timestamp_time - epoch_time).sec

    AzElConverter(component_manager=cm).create_antenna_obj()

    # BASE at original site
    cm.perform_reverse_transform(
        [ska_epoch_tai_timestamp, 322.8709276, 41.3703589]
    )
    t0, ra0, dec0 = cm.actual_pointing

    EXPECTED_RA_BASE = "15:31:50.9"
    EXPECTED_DEC_BASE = "10:15:51.4"

    assert t0 == timestamp_str
    assert ra0 == EXPECTED_RA_BASE
    assert dec0 == EXPECTED_DEC_BASE

    # SHIFT: move site by +1 deg lat/lon
    changed = deepcopy(ARRAY_LAYOUT)
    changed["location"]["geodetic"]["lat"] = (
        ARRAY_LAYOUT["location"]["geodetic"]["lat"] + 1.0
    )
    changed["location"]["geodetic"]["lon"] = (
        ARRAY_LAYOUT["location"]["geodetic"]["lon"] + 1.0
    )
    cm.array_layout = changed

    AzElConverter(component_manager=cm).create_antenna_obj()

    cm.perform_reverse_transform(
        [ska_epoch_tai_timestamp, 322.8709276, 41.3703589]
    )
    t1, ra1, dec1 = cm.actual_pointing

    EXPECTED_RA_SHIFT = "15:35:30.5"
    EXPECTED_DEC_SHIFT = "11:09:01.37"

    assert t1 == timestamp_str
    assert ra1 == EXPECTED_RA_SHIFT
    assert dec1 == EXPECTED_DEC_SHIFT
