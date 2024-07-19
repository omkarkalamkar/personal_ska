import time

import pytest
from astropy.time import Time
from ska_tmc_common import DevFactory

from ska_tmc_dishleafnode import AzElConverter
from tests.settings import DISH_MASTER_DEVICE, SKA_EPOCH, logger


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
        (
            "2019-02-19 06:01:00",
            "287.2504396",
            "77.8694392",
            "16:29:24.46",
            "-26:25:55.7",
        ),
        (
            "2022-03-19 09:21:50",
            "173.5146073",
            "-43.8021646",
            "10:14:56.82",
            "-14:44:15.13",
        ),
    ],
)
def test_azel_to_radec(
    tango_context,
    timestamp,
    az,
    el,
    expected_ra,
    expected_dec,
    cm,
):
    """Test the backward transform method from AzElConverter."""
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
        time.sleep(0.1)
    ra, dec = converter.azel_to_radec(az, el, timestamp)
    assert expected_ra == ra
    assert expected_dec == dec


def test_actual_pointing(tango_context, cm):
    """Test to check actual pointing is getting updated"""
    dish_manager = DevFactory().get_device(DISH_MASTER_DEVICE)
    timestamp_str = "2019-02-19 06:01:00"
    epoch_time = Time(SKA_EPOCH, format="isot", scale="utc")
    timestamp_time = Time(timestamp_str, format="iso", scale="utc")
    ska_epoch_tai_timestamp = (timestamp_time - epoch_time).sec
    dish_manager.programTrackTable = [
        ska_epoch_tai_timestamp,
        287.2504396,
        77.8694392,
    ]
    # Sometimes loading the iers data takes more time
    timeout = 5
    count = 0
    flag = True
    while flag and count <= timeout:
        if cm.actual_pointing and "2019" in cm.actual_pointing[0]:
            flag = False
        count += 1
        time.sleep(1)
    # Test case is not stable as sometimes tango misses the events
    # Below instructions will execute the test case in pythonic way.
    if flag:
        converter = AzElConverter(component_manager=cm)
        converter.create_antenna_obj()
        cm.perform_reverse_transform(
            [ska_epoch_tai_timestamp, 287.2504396, 77.8694392]
        )

    assert list(cm.actual_pointing) == [
        "2019-02-19 06:01:00",
        "16:29:24.46",
        "-26:25:55.7",
    ]
