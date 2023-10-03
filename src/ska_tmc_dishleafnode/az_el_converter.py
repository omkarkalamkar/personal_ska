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
import logging

from astropy import units as u
from astropy.coordinates import Angle
from katpoint import RefractionCorrection, Target
from ska_tmc_common.dish_utils import DishHelper

logger = logging.getLogger(__name__)


class AzElConverter:
    """Class to convert Right ascension(Ra) and Declination(Dec)
    values into Azimuth(Az) and Elevation(El)"""

    def __init__(self, component_manager) -> None:
        """
        Args:
            component_manager (DishLNComponent Manager): Dish LN component
        """
        self.component_manager = component_manager
        self.dish_helper = DishHelper()
        self.refraction_correction = RefractionCorrection()
        # The values for temprature, pressure and humidity are considered
        # arbitarily, acutal data will be used when a weather station is
        # available.
        self.weather_data = {
            "temprature": 30.0,
            "pressure": 900.0,
            "humidity": 10,
        }

    def create_antenna_obj(self) -> None:
        """This method identifies the KATPoint.
        Antenna object to be used from the Dish Number."""
        antennas = self.dish_helper.get_dish_antennas_list()

        for antenna in antennas:
            if antenna.name == self.component_manager.dish_id:
                self.component_manager.observer = antenna

    def point(self, right_ascension: str, declination: str, timestamp: str) -> list:
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
        return self.forward_transform(right_ascension, declination, timestamp)

    def backward_transform(self, az_value: u.rad, el_value: u.rad, timestamp: str) -> list:
        """This method converts given Azimuth/Elevation to RA/Dec after
        reversing the refraction correction and performing the topocentric and
        geocentric conversions.

        :param az_value: The Azimuth value of Actual Pointing.
        :dtype: Radians.
        :param el_value: The Elevation value of Actual Pointing.
        :dtype: Radians.

        :return: List of RA and Dec values in Hours Minutes Seconds and Degree
            Minutes Seconds respectively.
        """

        refraction_removed_el = self.refraction_correction.reverse(
            el_value,
            self.weather_data["temprature"],
            self.weather_data["pressure"],
            self.weather_data["humidity"],
        )
        elevation_angle = Angle(refraction_removed_el, u.rad)
        azimuth_angle = Angle(az_value, u.rad)
        target = Target.from_azel(
            azimuth_angle,
            elevation_angle,
        )
        ra_dec = target.radec(timestamp=timestamp, antenna=self.component_manager.observer)
        logger.info(
            "The Right Ascension is %s and the Declination is %s after backward transform",
            ra_dec.ra.hms,
            ra_dec.dec.dms,
        )
        return [ra_dec.ra.hms, ra_dec.dec.dms]

    def forward_transform(self, right_ascension: str, declination: str, timestamp: str) -> list:
        """This method invokes the katpoint commands to do the forward transform required
        for pointing a celestial object.
        Forward Transform ie: Geocentric conversion then topocentric and then refraction
        correction.

        :param right_ascension: Right Ascension value
        :dtype: string in hours:minutes:seconds form
        :param declination: Declination value.
        :dtype: string in the form of "degree:minutes:seconds"
            dec_value (str): Dec Value in degree:arc_minutes:arc_sec

        Return:
            az_el_coordinates (list)
        """
        target = Target.from_radec(right_ascension, declination)
        azel = target.azel(timestamp, self.component_manager.observer)
        refraction_corrected_el = self.refraction_correction.apply(
            azel.alt.rad,
            self.weather_data["temprature"],
            self.weather_data["pressure"],
            self.weather_data["humidity"],
        )
        refraction_corrected_angle = Angle(refraction_corrected_el, u.rad)
        logger.info(
            "The Azimuth value is %s and the Elevation is %s after forward transform.",
            azel.az.deg,
            refraction_corrected_angle.deg,
        )
        return [
            azel.az.deg,
            refraction_corrected_angle.deg,
        ]
