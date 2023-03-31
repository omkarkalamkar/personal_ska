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
from ska_telmodel.data import TMData

from ska_tmc_dishleafnode.manager.component_manager import (
    DishLNComponentManager,
)

from .utils import dd_to_dms


class AntennaLocation:
    """class to init antenna location parameters"""

    def __init__(self):
        "Class constructor"
        self.latitude = 0.0
        self.longitude = 0.0
        self.height = 0.0

    def get_latitude(self):
        """Added to resolve pylint  too-few-public-methods"""
        return self.latitude


class AntennaParams:
    """Class to define antenna parameters"""

    def __init__(self):
        """AntennaParams Constructor"""
        self.antenna_station_name = ""
        self.antenna_location = AntennaLocation()
        self.dish_diameter = 0.0

    def get_station_name(self):
        """Added to resolve pylint  too-few-public-methods"""
        return self.antenna_station_name


def get_antenna_params(antenna_params):
    """Method to return object of class AntennaParams"""
    antenna_location = AntennaLocation()
    antenna_param = AntennaParams()
    antenna_location.latitude = float(
        antenna_params["location"]["geodetic"]["lat"]
    )
    antenna_location.longitude = float(
        antenna_params["location"]["geodetic"]["lon"]
    )
    antenna_location.height = float(
        antenna_params["location"]["geodetic"]["h"]
    )
    antenna_param.antenna_location = antenna_location
    antenna_param.dish_diameter = antenna_params["diameter"]
    antenna_param.antenna_station_name = antenna_params["station_name"]
    return antenna_param


class AzElConverter:
    """Class to convert Right ascension(Ra) and Declination(Dec)
    values into Azimuth(Az) and Elevation(El)"""

    def __init__(self, log, dish_device_name):
        self.logger = log
        self.dish_device_name = dish_device_name
        self.device_data = DishLNComponentManager(
            self.dish_device_name, self.logger
        )
        self.device_data.set_dish_name_number(dish_device_name)

    def create_antenna_obj(self):
        """This method identifies the KATPoint.
        Antenna object to be used from the Dish Number."""
        antennas = []
        try:
            sources = [
                "gitlab://gitlab.com/ska-telescope/"
                + "sdp/ska-sdp-tmlite-repository?main#tmdata"
            ]
            layout_path = "instrument/ska1_mid/layout/mid-layout.json"
            antenna_params = TMData(sources)[layout_path].get_dict()

            for receptor in range(len(antenna_params["receptors"])):
                receptor_params = get_antenna_params(
                    antenna_params["receptors"][receptor]
                )

                input_to_antenna = f"{receptor_params.antenna_station_name},\
                        {dd_to_dms(receptor_params.antenna_location.latitude)},\
                            {dd_to_dms(receptor_params.antenna_location.longitude)},\
                                {receptor_params.antenna_location.height},\
                                    {receptor_params.dish_diameter}"
                antennas.append(katpoint.Antenna(input_to_antenna))

        except OSError as err:
            self.logger.exception(err)
            raise f"OSError.'{err}'in AzElConverter.create_antenna_obj."

        except ValueError as verr:
            self.logger.exception(verr)
            raise f"ValueError.'{verr}'in AzElConverter.create_antenna_obj."

        for antenna in antennas:
            if antenna.name == self.device_data.dish_number:
                self.device_data.observer = antenna

    def point(self, ra_value, dec_value, timestamp):
        """This method converts Target RaDec coordinates
        to the AzEl coordinates.It is called continuosly
        from Track command (in a thread) at interval
        of 50ms till the StopTrack command is invoked.
        """
        # Create KATPoint Target object
        target = katpoint.Target.from_radec(ra_value, dec_value)
        # obtain az el co-ordinates for dish
        azel = target.azel(timestamp, self.device_data.observer)
        # list of az el co-ordinates
        az_el_coordinates = [azel.az.deg, azel.alt.deg]
        return az_el_coordinates
