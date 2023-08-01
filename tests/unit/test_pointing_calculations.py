import logging

import pytest
from ska_tmc_common.dish_utils import DishHelper

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.manager import DishLNComponentManager


@pytest.mark.SKA_mid
def test_pointing_calculations():
    """Function to test AzEl conversion"""
    ra = "02:31:50.88"
    dec = "89:15:51.4"
    timestamp = "2019-02-19 06:01:00"
    dish_dev_name = "ska001/dish/master"
    logger = logging.getLogger(__name__)
    component_manager = DishLNComponentManager(logger=logger, dish_dev_name=dish_dev_name)
    pointing_calc = AzElConverter(component_manager)
    pointing_calc.create_antenna_obj()
    azel = pointing_calc.point(ra, dec, timestamp)
    dish_helper = DishHelper()
    azimuth = dish_helper.dd_to_dms(azel[0])  # azel[0] is an Azimuth value in degree
    assert azimuth == "0:27:23.1738"
