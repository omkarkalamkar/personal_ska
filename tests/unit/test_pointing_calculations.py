import logging

import pytest

from ska_tmc_dishleafnode.az_el_converter import AzElConverter


@pytest.mark.SKA_mid
def test_pointing_calculations():
    """Function to test AzEl conversion"""
    ra = "21:08:47.92"
    dec = "-88:57:22.9"
    timestamp = "2021-04-29 05:36:50.031567"
    dish_dev_name = "M000/elt/master"
    logger = logging.getLogger(__name__)
    pointing_calc = AzElConverter(logger, dish_dev_name)
    pointing_calc.create_antenna_obj()
    azel = pointing_calc.point(ra, dec, timestamp)
    assert azel[0] == 180.03706249592315
