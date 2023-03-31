import logging

import pytest

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.device_data import DeviceData


@pytest.mark.SKA_mid
def test_pointing_calculations():
    """Function to test AzEl conversion"""
    ra = "21:08:47.92"
    dec = "-88:57:22.9"
    timestamp = "2021-04-29 05:36:50.031567"
    logger = logging.getLogger(__name__)
    device_data = DeviceData.get_instance()
    device_data.set_dish_name_number("M000/elt/master")
    pointing_calc = AzElConverter(logger)
    pointing_calc.create_antenna_obj()
    azel = pointing_calc.point(ra, dec, timestamp)
    assert azel[0] == 180.03706249592315
