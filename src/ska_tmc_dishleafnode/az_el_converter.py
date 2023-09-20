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


class AzElConverter:
    """Class to convert Right ascension(Ra) and Declination(Dec)
    values into Azimuth(Az) and Elevation(El)"""

    def __init__(self, component_manager) -> None:
        """
        Args:
            component_manager (DishLNComponent Manager): Dish LN component
        """
        self.component_manager = component_manager

    def create_antenna_obj(self) -> None:
        """This method identifies the KATPoint.
        Antenna object to be used from the Dish Number."""
        dish_helper = DishHelper()
        antennas = dish_helper.get_dish_antennas_list()

        for antenna in antennas:
            if antenna.name == self.component_manager.dish_id:
                self.component_manager.observer = antenna

    def point(self, ra_value, dec_value, timestamp) -> list:
        """This method converts Target RaDec coordinates
        to the AzEl coordinates.It is called continuosly
        from Track command (in a thread) at interval
        of 50ms till the StopTrack command is invoked.
        Args:
            ra_value (str): RA value in hours:minutes:sec
            dec_value (str): Dec Value in degree:arc_minutes:arc_sec
            timestamp(str): utc timestamp in string format
        Return:
            az_el_coordinates (list)
        """
        # Create KATPoint Target object
        target = katpoint.Target.from_radec(ra_value, dec_value)
        # obtain az el co-ordinates for dish
        azel = target.azel(timestamp, self.component_manager.observer)
        # list of az el co-ordinates
        az_el_coordinates = [azel.az.deg, azel.alt.deg]
        return az_el_coordinates
