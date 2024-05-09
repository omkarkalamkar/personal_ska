import datetime
import time

import pytest
from ska_tmc_common import DevFactory

from ska_tmc_dishleafnode import AzElConverter
from tests.settings import DISH_MASTER_DEVICE, WEATHER_DATA, logger


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
    tango_context, timestamp, az, el, expected_ra, expected_dec, cm, iers_data
):
    """Test the backward transform method from AzElConverter."""
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
        time.sleep(0.1)
    ra, dec = converter.azel_to_radec(az, el, timestamp, WEATHER_DATA)
    assert expected_ra == ra
    assert expected_dec == dec


def test_actual_pointing(tango_context, cm, iers_data):
    """Test to check actual pointing is getting updated"""
    cm.iers_a = iers_data
    EXTEND_MILLISECONDS = 100
    dish_manager = DevFactory().get_device(DISH_MASTER_DEVICE)
    timestamp_str = datetime.datetime.strptime(
        "2019-02-19 06:01:00", "%Y-%m-%d %H:%M:%S"
    )
    dt_utc = timestamp_str.replace(tzinfo=datetime.timezone.utc)
    extended_time = dt_utc + datetime.timedelta(
        milliseconds=EXTEND_MILLISECONDS
    )
    utc_timestamp = extended_time.timestamp() * 1000
    dish_manager.programTrackTable = [utc_timestamp, 287.2504396, 77.8694392]
    # Sometimes loading the iers data takes more time
    timeout = 60
    count = 0
    flag = True
    while flag and count <= timeout:
        if cm.actual_pointing and "2019" in cm.actual_pointing[0]:
            flag = False
        count += 1
        time.sleep(0.1)

    assert list(cm.actual_pointing) == [
        "2019-02-19 06:01:00",
        "16:29:24.46",
        "-26:25:55.7",
    ]
