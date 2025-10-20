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
from ska_tmc_common.v3.dish_utils import DishHelper

configure_logging()
logger = logging.getLogger(__name__)


class AzElConverter:
    """Class to convert Right ascension(Ra) and Declination(Dec)
    values into Azimuth(Az) and Elevation(El)."""

    def __init__(self: AzElConverter, component_manager) -> None:
        """
        Args:
            component_manager (DishLNComponentManager): Dish LN component
        """
        self.component_manager = component_manager
        # DishHelper now takes a dict via `antenna_data` (not JSON string).
        # Instantiate it lazily in create_antenna_obj to use the latest layout.
        self.dish_helper: DishHelper | None = None
        self.refraction_correction = TroposphericRefraction()
        # The values for temperature, pressure and humidity are considered
        self.weather_data = {
            "temperature": 30.0,
            "pressure": 900.0,
            "humidity": 0.10,  # Humidity is a fraction (0–1)
        }

    def create_antenna_obj(self) -> None:
        """Create antenna object from array layout and set observer."""
        layout = getattr(self.component_manager, "array_layout", None)
        if not layout:
            logger.warning("No array_layout found; observer will not be set.")
            return

        # Pass the dict (or 1-item list[dict]) straight in
        try:
            self.dish_helper = DishHelper(antenna_data=layout)
        except TypeError:
            # old signature fallback, if needed
            self.dish_helper = DishHelper(layout)

        try:
            antenna = (
                self.dish_helper.get_dish_antenna()
                if hasattr(self.dish_helper, "get_dish_antenna")
                else self.dish_helper.get_dish_antennas_data()
            )
        except Exception as e:
            logger.exception("Cannot build antenna from layout: %s", e)
            return

        self.component_manager.observer = antenna
        logger.info(
            "Observer set to %s", getattr(antenna, "name", "<antenna>")
        )

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
                "After refraction: Az=%s deg, El=%s deg",
                refraction_corrected_azel.az.deg,
                refraction_corrected_azel.alt.deg,
            )
        except Exception as exception:
            message = (
                "Exception occurred while applying refraction "
                f"correction: {exception}"
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
        Get Az/El for a non-sidereal object and apply refraction correction.

        :param target_name: Name of the non-sidereal body
        :param timestamp: Timestamp for observation
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
        declination: str | float,
        timestamp: str,
    ) -> list[float]:
        """Convert RA/Dec to Az/El and apply refraction.

        Args:
            right_ascension: RA value (H:M:S string or float degrees )
            declination: Dec value (D:M:S string or float degrees per )
            timestamp: UTC timestamp string

        Returns:
            [Az deg, El deg]
        """
        az_el_coordinates = []
        try:
            logger.debug(
                "Converting RA/Dec to Az/El. RA=%s, Dec=%s, ts=%s",
                right_ascension,
                declination,
                timestamp,
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
        """Convert Az/El (deg) to RA/Dec (HMS/DMS), reversing refraction."""
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

        # Preload IERS A table for astropy
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
        logger.debug("Converted Az/El to RA/Dec: RA=%s, Dec=%s", ra, dec)
        return [ra, dec]

    def radec_to_azel(
        self: AzElConverter,
        # The ra/dec can be str or float
        # as per ADR-106 the c1 and c2 (ra and dec)
        # may be provided as float degrees
        right_ascension: str | float,
        declination: str | float,
        timestamp: str,
    ) -> List[float]:
        """Forward transform RA/Dec to Az/El and apply refraction.

        Args:
            right_ascension: RA value (H:M:S string or float degrees)
            declination: Dec value (D:M:S string or float degrees)
            timestamp: UTC timestamp string

        Returns:
            [Az deg, El deg]
        """
        ra = right_ascension
        dec = declination
        if isinstance(right_ascension, float):
            ra = Angle(right_ascension, unit=u.degree)
            dec = Angle(declination, unit=u.degree)

        try:
            target = Target.from_radec(ra, dec)

            # Preload IERS A table for astropy
            with iers.earth_orientation_table.set(
                self.component_manager.iers_a
            ):
                azel = target.azel(timestamp, self.component_manager.observer)

            return self.apply_refraction_correction(azel)

        except ValueError as value_error:
            message = str(value_error)
            logger.error("Invalid RA/Dec values provided, Error: %s ", message)
            raise Exception(message) from value_error

        except Exception as exception:
            message = str(exception)
            logger.exception(
                "Failed to convert RA/Dec to Az/El, Exception: %s ", message
            )
            raise Exception(message) from exception
