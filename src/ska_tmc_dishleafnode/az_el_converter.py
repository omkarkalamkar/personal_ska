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
        self.refraction_correction = RefractionCorrection()

    def create_antenna_obj(self) -> None:
        """This method identifies the KATPoint.
        Antenna object to be used from the Dish Number."""
        dish_helper = DishHelper()
        antennas = dish_helper.get_dish_antennas_list()

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

        return self.forward_transform(
            right_ascension=right_ascension, declination=declination, timestamp=timestamp
        )

    def backward_transform(self, az_value, el_value, timestamp) -> list:
        """This method converts given Azimuth/Elevation to RA/Dec after
        reversing the refraction correction and performing the topocentric and
        geocentric conversions.

        :param az_value: The Azimuth value of Actual Pointing.
        :dtype: Radians.
        :param el_value: The Elevation value of Actual Pointing.
        :dtype: Radians.

        :return: List of RA and Dec values in degrees.
        """

        refraction_corrected_el = self.refraction_correction.reverse(el_value, 0.0, 0.0, 0.0)
        elevation_angle = Angle(refraction_corrected_el, u.rad)
        elevation_angle = elevation_angle.dms
        elevation_angle = f"{int(elevation_angle[0])}\
            :{abs(int(elevation_angle[1]))}:{abs(round(elevation_angle[2],2))}"
        azimuth_angle = Angle(az_value, u.deg)
        azimuth_angle = azimuth_angle.dms
        azimuth_angle = (
            f"{int(azimuth_angle[0])}:{int(azimuth_angle[1])}:{round(azimuth_angle[2],2)}"
        )
        target = Target.from_azel(
            azimuth_angle,
            elevation_angle,
        )
        ra_dec = target.radec(timestamp=timestamp, antenna=self.component_manager.observer)
        return [ra_dec.ra.deg, ra_dec.dec.deg]

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

        ra_angle = Angle(right_ascension, u.hourangle)
        dec_angle = Angle(declination, u.deg)
        target = Target.from_radec(ra_angle, dec_angle)  # Create KATPoint Target object
        azel = target.azel(
            timestamp, self.component_manager.observer
        )  # Does geocentric and topocentric conversions and returns SkyCord object.
        elevation_angle = Angle(azel.alt.deg, u.deg)
        refraction_corrected_el_in_rad = self.refraction_correction.apply(
            elevation_angle.rad, 0.0, 0.0, 0.0
        )  # Does the refraction corrections(Atmospheric conversion ADR-76)
        refraction_corrected_angle = Angle(refraction_corrected_el_in_rad, u.rad)
        return [
            azel.az.deg,
            refraction_corrected_angle.deg,
        ]  # list of az el co-ordinates in degrees
