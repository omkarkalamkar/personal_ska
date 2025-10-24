import time

import pytest
from astropy.time import Time
from ska_tmc_common.v3.dish_utils import DishHelper

from ska_tmc_dishleafnode import AzElConverter
from tests.settings import ARRAY_LAYOUT, SKA_EPOCH, logger


@pytest.mark.test
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
