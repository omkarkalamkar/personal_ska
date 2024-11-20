from time import sleep

import pytest
from astropy.utils import iers

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.constants import IERS_DATA_STORAGE_PATH
from tests.settings import logger

NSR_BODIES = {
    "Sun": [90.7870534, 21.4027101],
    "Moon": [272.5860536, -28.2928461],
    "Mars": [99.6443372, -40.9555322],
    "Jupiter": [355.1530885, 81.7461327],
    "Saturn": [77.0803018, 63.8381432],
    "Neptune": [93.8862928, 6.4735292],
    "Venus": [75.5221999, 62.6933571],
    "Mercury": [93.2118997, 6.4246602],
}


def test_point_at_body(
    cm_without_er_lp,
):
    """Function to test AzEl conversion"""
    cm = cm_without_er_lp
    timestamp = '2019-02-19 06:01:00'
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
    az = None
    el = None
    for body_name in list(NSR_BODIES.keys()):
        try:
            az, el = converter.point_to_body(body_name, timestamp)
            if az:
                break
        except Exception:
            continue
    az = round(az, 5)
    el = round(el, 5)
    logger.info("Az is: %s", az)
    logger.info("El is: %s", el)
    assert az == round(NSR_BODIES[body_name][0], 5)
    assert el == round(NSR_BODIES[body_name][1], 5)
