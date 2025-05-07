""" AzElConverter:
This module defines the AzElConverter class,
which is used to convert given Ra and Dec values into AzEl."""
# Standard Python imports
from __future__ import annotations

import logging
from typing import Any, List

from astropy import units as u
from astropy.coordinates import AltAz, Angle
from astropy.utils import iers
from katpoint import Target, TroposphericRefraction
from katpoint.conversion import angle_to_string
from ska_ser_logging import configure_logging
from ska_tmc_common.dish_utils import DishHelper

configure_logging()
logger = logging.getLogger(__name__)


class AzElConverter:
    """Class to convert Right ascension(Ra) and Declination(Dec)
    values into Azimuth(Az) and Elevation(El)"""

    def __init__(self: AzElConverter, component_manager) -> None:
        """
        Args:
            component_manager (DishLNComponent Manager): Dish LN component
        """
        self.component_manager = component_manager
        self.dish_helper = DishHelper()
        self.refraction_correction = TroposphericRefraction()
        # The values for temperature, pressure and humidity are considered
        # arbitarily, acutal data will be used when a weather station is
        # available.
        self.weather_data = {
            "temperature": 30.0,
            "pressure": 900.0,
            "humidity": 0.10,
            # Humidity is now a fraction instead of percentage
        }

    def create_antenna_obj(self: AzElConverter) -> None:
        """This method identifies the KATPoint.
        Antenna object to be used from the Dish Number."""
        antennas = self.dish_helper.get_dish_antennas_list()
        for antenna in antennas:
            if self.component_manager.dish_id:
                if (
                    antenna.name.lower()
                    == self.component_manager.dish_id.lower()
                ):
                    self.component_manager.observer = antenna

    def apply_refraction_correction(
        self: AzElConverter, azel: AltAz
    ) -> List[float]:
        """Apply refraction correction on given AzEl."""
        try:
            refraction_corrected_azel = self.refraction_correction.refract(
                azel,
                self.weather_data["pressure"] * u.hPa,
                self.weather_data["temperature"] * u.deg_C,
                self.weather_data["humidity"],
            )
            logger.debug(
                "The Az value is: %s and the El is %s : after "
                "forward transform.",
                refraction_corrected_azel.az.deg,
                refraction_corrected_azel.alt.deg,
            )
        except Exception as exception:
            message = (
                "Exception occurred while applying refraction correction: "
                + str(exception)
            )
            logger.exception(message)
            raise Exception(message) from exception

        return [
            refraction_corrected_azel.az.deg,
            refraction_corrected_azel.alt.deg,
        ]

    def point_to_body(
        self: AzElConverter, target_name: str, timestamp: str
    ) -> List[float]:
        """
        This method calls the Katpoint API to get the Azimuth and Elevation for
        a non sidereal object and applies the refraction correction to it.

        :param target_name: Name of the non-sidereal body
        :type target_name: str
        :param timestamp: Timestamp for observation
        :type timestamp: str
        """
        refraction_corrected_azel = []
        try:
            non_sidereal_target = Target(f"{target_name}, special")
            logger.debug(
                "Created non-sidereal target: %s", non_sidereal_target
            )
            with iers.earth_orientation_table.set(
                self.component_manager.iers_a
            ):
                azel = non_sidereal_target.azel(
                    timestamp, self.component_manager.observer
                )

            refraction_corrected_azel = self.apply_refraction_correction(azel)

        except ValueError as value_error:
            message = str(value_error)
            raise Exception(message) from value_error

        except Exception as exception:
            message = str(exception)
            raise Exception(message) from exception
        return refraction_corrected_azel

    def point(
        self: AzElConverter,
        right_ascension: str | float,
        declination: str,
        timestamp: str,
    ) -> list[float]:
        """This method converts Target RaDec coordinates
        to the AzEl coordinates.It is called continuously
        from Track command (in a thread) at interval
        of 50ms till the StopTrack command is invoked.
        Args:
            ra_value (str): RA value in hours:minutes:sec
            dec_value (str): Dec Value in degree:arc_minutes:arc_sec
            timestamp(str): utc timestamp in string format
        return:
            az_el_coordinates (list)
        """
        az_el_coordinates = []
        try:
            logger.debug(
                "Converting Target RaDec coordinates to the AzEl coordinates"
            )
            az_el_coordinates = self.radec_to_azel(
                right_ascension, declination, timestamp
            )

        except Exception as exception:
            message = (
                "Exception occurred while converting RaDec to AzEl: "
                + str(exception)
            )
            logger.exception(message)
            raise Exception(message) from exception
        return az_el_coordinates

    def azel_to_radec(
        self: AzElConverter,
        az_value: float,
        el_value: float,
        timestamp: str,
    ) -> List[str | Any]:
        """This method converts given Azimuth/Elevation to RA/Dec after
        reversing the refraction correction and performing the topocentric and
        geocentric conversions.

        :param az_value: The Azimuth value of Actual Pointing.
        :dtype: Degrees.
        :param el_value: The Elevation value of Actual Pointing.
        :dtype: Degrees.

        :return: List of RA and Dec values in Hours Minutes Seconds and Degree
                 Minutes Seconds respectively.
        """

        azel = AltAz(az=Angle(az_value, u.deg), alt=Angle(el_value, u.deg))
        refraction_removed_azel = self.refraction_correction.unrefract(
            azel,
            self.weather_data["pressure"] * u.hPa,
            self.weather_data["temperature"] * u.deg_C,
            self.weather_data["humidity"],
        )

        target = Target.from_azel(
            refraction_removed_azel.az,
            refraction_removed_azel.alt,
        )

        # Preloading the IERS A chart for Astrop's usage.
        with iers.earth_orientation_table.set(self.component_manager.iers_a):
            ra_dec = target.radec(
                timestamp=timestamp, antenna=self.component_manager.observer
            )

        ra = angle_to_string(
            ra_dec.ra, unit=u.hour, precision=2, show_unit=False
        )
        dec = angle_to_string(
            ra_dec.dec, unit=u.deg, precision=2, show_unit=False
        )
        logger.debug(
            "The Ra value is : %s and the Dec value is : %s after "
            "backward transform",
            ra,
            dec,
        )
        return [ra, dec]

    def radec_to_azel(
        self: AzElConverter,
        # The ra/dec can str or float
        # as per ADR-106 the c1 and c2 ie ra and dec
        # are expressed in the form of float
        right_ascension: str | float,
        declination: str | float,
        timestamp: str,
    ) -> List[float]:
        """This method invokes the katpoint commands to do the forward
        transform required for pointing a celestial object.
        Forward Transform ie: Geocentric conversion then topocentric and then
        refraction correction.

        :param right_ascension: Right Ascension value
        :dtype: string in hours:minutes:seconds form
        :param declination: Declination value.
        :dtype: string in the form of "degree:minutes:seconds"
            dec_value (str): Dec Value in degree:arc_minutes:arc_sec

        Return:
            az_el_coordinates (list[degrees])
        """
        ra = right_ascension
        dec = declination
        if isinstance(right_ascension, float):
            ra = Angle(right_ascension, unit=u.degree)
            dec = Angle(declination, unit=u.degree)

        refraction_corrected_azel = []
        try:
            target = Target.from_radec(ra, dec)

            # Preloading the IERS A chart for Astrop's usage.
            with iers.earth_orientation_table.set(
                self.component_manager.iers_a
            ):
                azel = target.azel(timestamp, self.component_manager.observer)

            refraction_corrected_azel = self.apply_refraction_correction(azel)

        except ValueError as value_error:
            message = str(value_error)
            logger.error("Invalid RA/Dec values provided, Error: %s ", message)
            raise Exception(message) from value_error

        except Exception as exception:
            message = str(exception)
            logger.exception(
                "Failed to convert RA/Dec to Az/El, Exception: %s ",
                message,
            )
            raise Exception(message) from exception

        return refraction_corrected_azel
