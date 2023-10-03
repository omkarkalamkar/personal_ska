import logging

import numpy as np
import pytest

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from tests.settings import DISH_MASTER_DEVICE, create_cm

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "ra, dec, timestamp, expected_az, expected_el",
    [
        pytest.param("16:29:24.46", "-26:25:55.7", "2019-02-19 06:01:00", 5.0134659, 1.3590781),
        pytest.param("2:31:50.9", "89:15:51.4", "2019-02-19 06:01:00", 0.0079663, -0.5381385),
        pytest.param("10:14:56.82", "-14:44:15.13", "2022-03-19 09:21:50", 3.0284012, -0.7644920),
    ],
)
def test_pointing_calculations(
    ra: str, dec: str, timestamp: str, expected_az: float, expected_el: float
):
    """Function to test AzEl conversion"""
    cm = create_cm(DISH_MASTER_DEVICE)
    converter = AzElConverter(component_manager=cm)
    converter.create_antenna_obj()
    az, el = converter.forward_transform(ra, dec, timestamp)
    az = round(np.deg2rad(az), 7)
    el = round(np.deg2rad(el), 7)
    assert az == expected_az
    assert el == expected_el
