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
                else self.dish_helper.get_dish_antenna()
            )
        except Exception as e:
            logger.exception("Cannot build antenna from layout: %s", e)
            return

        self.component_manager.observer = antenna
        logger.debug(
            "Observer set to %s", getattr(antenna, "name", "<antenna>")
        )

    def apply_refraction_correction(
        self: AzElConverter, azel: AltAz
    ) -> List[float]:
        """Apply refraction correction on given AzEl."""
        try:
            refraction_corrected_azel = self.refraction_correction.refract(
                azel,
                self.component_manager.pressure * u.hPa,
                self.component_manager.temperature * u.deg_C,
                self.component_manager.humidity,
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
            logger.debug(" %s", non_sidereal_target)
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
            self.component_manager.pressure * u.hPa,
            self.component_manager.temperature * u.deg_C,
            self.component_manager.humidity,
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


class AzElConverter_v2(AzElConverter):
    """Class to convert ICRS, special, TLE, altaz, etc reference frame
    values into Azimuth(Az) and Elevation(El).
    This class addressed the missing projection and trajectory functionality
    in older class.
    """

    def __init__(self, component_manager):
        super().__init__(component_manager=component_manager)

    def point(
        self: AzElConverter_v2,
        right_ascension: str | float | None = None,
        declination: str | float | None = None,
        timestamp: str | None = None,
    ) -> List[float]:
        """
        Get Az, El and apply refraction correction.

        Args:
            timestamp: Timestamp for observation.

        Returns:
            List[float]: Azimuth and Elevation in degrees after refraction
            correction.
        """

        refraction_corrected_azel = []
        try:
            x_in_rad, y_in_rad = self.get_offset_in_rad(
                self.component_manager.fixed_x_offset,
                self.component_manager.fixed_y_offset,
            )
            with iers.earth_orientation_table.set(
                self.component_manager.iers_a
            ):
                az, el = self.component_manager.antenna_target.plane_to_sphere(
                    x_in_rad,
                    y_in_rad,
                    timestamp=timestamp,
                    projection_type=self.component_manager.projection_name,
                    coord_system=self.component_manager.projection_alignment,
                )
            azel = AltAz(az=Angle(az, u.rad), alt=Angle(el, u.rad))
            refraction_corrected_azel = self.apply_refraction_correction(azel)

        except ValueError as value_error:
            message = str(value_error)
            raise Exception(message) from value_error

        except Exception as exception:
            message = str(exception)
            raise Exception(message) from exception
        return refraction_corrected_azel

    def get_offset_in_rad(self, x: float, y: float) -> tuple:
        """Get the offset in radian

        Args:
            x: Offset in arcseconds along x-axis.
            y: Offset in arcseconds along y-axis.
        Returns:
            tuple[float, float]: Offset values in radians.
        """
        return Angle(x, u.arcsec).rad, Angle(y, u.arcsec).rad

    def _calculate_azel_with_trajectory(
        self: AzElConverter_v2,
        target: Target,
        x_offset: float,
        y_offset: float,
        timestamp: str | None = None,
    ) -> List[float]:
        """Calculate Azimuth and Elevation for a target with trajectory
        offsets.
        Compute the azimuth and elevation for the given `target` by
        applying the provided trajectory offsets (x/y) and performing
        atmospheric refraction correction.

        Args:
            target (Target): katpoint Target object representing the
                reference target.
            x_offset (float): X offset in arcseconds to apply to the target.
            y_offset (float): Y offset in arcseconds to apply to the target.
            timestamp (str | None): timestamp for the observation

        Returns:
            List[float]: [azimuth_deg, elevation_deg] in degrees after
            refraction correction.
        """

        refraction_corrected_azel = []
        try:
            azel = None
            x_in_rad, y_in_rad = self.get_offset_in_rad(
                x_offset,
                y_offset,
            )
            with iers.earth_orientation_table.set(
                self.component_manager.iers_a
            ):
                match self.component_manager.projection_alignment:
                    case "azel":
                        ref_azel = target.azel(
                            timestamp, self.component_manager.observer
                        )
                        (
                            az,
                            el,
                        ) = self.component_manager.plane_to_sphere_handler(
                            ref_azel.alt.rad,
                            x_in_rad,
                            y_in_rad,
                        )
                        azel = AltAz(az=Angle(az, u.rad), alt=Angle(el, u.rad))

                    case "radec":
                        radec = target.radec(
                            timestamp, self.component_manager.observer
                        )

                        (
                            ra,
                            dec,
                        ) = self.component_manager.plane_to_sphere_handler(
                            radec.ra.rad,
                            radec.dec.rad,
                            x_in_rad,
                            y_in_rad,
                        )
                        temp_target = Target.from_radec(ra, dec)
                        azel = temp_target.azel(
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
