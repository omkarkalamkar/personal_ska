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

from .device_data import DeviceData
from .utils import dd_to_dms


class AntennaLocation:
    """class to init antenna location parameters"""

    def __init__(self):
        "Class constructor"
        self.latitude = 0.0
        self.longitude = 0.0
        self.height = 0.0


class AntennaParams:
    """Class to define antenna parameters"""

    def __init__(self):
        """AntennaParams Constructor"""
        self.antenna_station_name = ""
        self.antenna_location = AntennaLocation()
        self.dish_diameter = 0.0


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

    def __init__(self, log):
        self.logger = log
        self.antennas = []

    def create_antenna_obj(self):
        """This method identifies the KATPoint.
        Antenna object to be used from the Dish Number."""
        try:
            device_data = DeviceData.get_instance()
            sources = [
                "gitlab://gitlab.com/ska-telescope/"
                + "sdp/ska-sdp-tmlite-repository?main#tmdata"
            ]
            layout_path = "instrument/ska1_mid/layout/mid-layout.json"
            antenna_params = TMData(sources)[layout_path].get_dict()

            for receptor in range(len(antenna_params["receptors"]) - 192):
                receptor_params = get_antenna_params(
                    antenna_params["receptors"][receptor]
                )

                input_to_antenna = f"{receptor_params.antenna_station_name},\
                        {dd_to_dms(receptor_params.antenna_location.latitude)},\
                            {dd_to_dms(receptor_params.antenna_location.longitude)},\
                                {receptor_params.antenna_location.height},\
                                    {receptor_params.dish_diameter}"
                self.antennas.append(katpoint.Antenna(input_to_antenna))

        except OSError as err:
            self.logger.exception(err)
            raise Exception(
                f"OSError.'{err}'in device_data.create_antenna_obj."
            )
        except ValueError as verr:
            self.logger.exception(verr)
            raise Exception(
                f"ValueError.'{verr}'in device_data.create_antenna_obj."
            )

        for antenna in self.antennas:
            if antenna.name == device_data.dish_number:
                device_data.observer = antenna

    def point(self, ra_value, dec_value, timestamp):
        """This method converts Target RaDec coordinates
        to the AzEl coordinates.It is called continuosly
        from Track command (in a thread) at interval
        of 50ms till the StopTrack command is invoked.
        """
        device_data = DeviceData.get_instance()
        # Create KATPoint Target object
        target = katpoint.Target.from_radec(ra_value, dec_value)
        # obtain az el co-ordinates for dish
        azel = target.azel(timestamp, device_data.observer)
        # list of az el co-ordinates
        az_el_coordinates = [azel.az.deg, azel.alt.deg]
        return az_el_coordinates

    def download_IERS_file(self):
        """This method performs one pointing calculation with
        dummy values to download the IERS file in advanced
        to the potinting calcualtions on DishLeafNode."""
        # Create an example radec target
        ra = "21:08:47.92"
        dec = "-88:57:22.9"
        target = katpoint.Target.from_radec(ra, dec)
        ant = katpoint.Antenna(
            "0001, -30:42:39.8d, 21:26:38d, 1086, \
                13.5, 1.1205 -171.762 8.4705, , 0.0"
        )
        timestamp = "2021-04-29 05:36:50.031567"
        azel = target.azel(timestamp, ant)
        self.logger.info("IERS file downloading is completed: '%s'", azel)
