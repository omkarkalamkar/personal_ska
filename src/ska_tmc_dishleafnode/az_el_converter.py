# -*- coding: utf-8 -*-
#
# This file is part of the DishLeafNode project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
""" AzElConverter:
This module defines the AzElConverter class,
which is used to convert given Ra and Dec values into AzEl."""
# Standard Python imports

import katpoint
from ska_tmc_common.dish_utils import DishHelper

from ska_tmc_dishleafnode.manager.component_manager import (
    DishLNComponentManager,
)


class AzElConverter:
    """Class to convert Right ascension(Ra) and Declination(Dec)
    values into Azimuth(Az) and Elevation(El)"""

    def __init__(self, log, dish_device_name):
        self.logger = log
        self.dish_device_name = dish_device_name
        self.dishln_cm = DishLNComponentManager(
            self.dish_device_name, self.logger
        )
        self.dishln_cm.set_dish_name_number(dish_device_name)

    def create_antenna_obj(self):
        """This method identifies the KATPoint.
        Antenna object to be used from the Dish Number."""
        dish_helper = DishHelper()
        antennas = dish_helper.get_dish_antennas_list()

        for antenna in antennas:
            if antenna.name == self.dishln_cm.dish_number:
                self.dishln_cm.observer = antenna

    def point(self, ra_value, dec_value, timestamp):
        """This method converts Target RaDec coordinates
        to the AzEl coordinates.It is called continuosly
        from Track command (in a thread) at interval
        of 50ms till the StopTrack command is invoked.
        """
        # Create KATPoint Target object
        target = katpoint.Target.from_radec(ra_value, dec_value)
        # obtain az el co-ordinates for dish
        azel = target.azel(timestamp, self.dishln_cm.observer)
        # list of az el co-ordinates
        az_el_coordinates = [azel.az.deg, azel.alt.deg]
        return az_el_coordinates
