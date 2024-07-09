from time import sleep

import pytest

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from tests.settings import logger


@pytest.mark.parametrize(
    "body_name, timestamp, expected_az, expected_el",
    [
        ("Sun", "2019-02-19 06:01:00", 90.7870535, 21.4058439),
    ],
)
@pytest.mark.temp
def test_point_at_body(
    body_name: str,
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
    az, el = converter.point_to_body(body_name, timestamp)
    az = round(az, 7)
    el = round(el, 7)
    logger.info("Az is: %s", az)
    logger.info("El is: %s", el)
    assert az == expected_az
    assert el == expected_el
