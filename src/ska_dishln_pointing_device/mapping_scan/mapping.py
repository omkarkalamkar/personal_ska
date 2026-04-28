"""This module provides base class for the mappings/patterns"""

from logging import Logger
from typing import Any, List, Tuple

import katpoint
import numpy as np
from astropy import units as u
from astropy.coordinates import Angle
from astropy.utils import iers
from katpoint import Target
from numpy import isnan, nan
from ska_trajectory.trajectory_names import TrajectoryName
from ska_tmc_dishleafnode.az_el_converter import (
    AzElConverter_v2 as AzElConverter,
)
from ska_dishln_pointing_device.mapping_scan.utils import (
    InvalidTargetDataError,
)

from katpoint.projection import (
    plane_to_sphere_arc,
    plane_to_sphere_sin,
    plane_to_sphere_tan,
    plane_to_sphere_car,
    plane_to_sphere_ssn,
    plane_to_sphere_stg,
)


class BaseScanMapping:
    """Base class for all scan mappings/patterns"""

    def __init__(
        self,
        component_manager,
        logger: Logger,
    ) -> None:
        self.target: str | None = None
        self.component_manager = component_manager
        self.logger = logger
        self.target = None
        self.main_target_ra = None
        self.main_target_dec = None
        self.ra_dec_target = None
        self.traj = None
        self.cadence = 0.0
        self.converter = AzElConverter(self.component_manager)
        self.projection_alignment = None
        self.reference_frame_handler = None
        self.ra = None
        self.dec = None
        self.az = None
        self.el = None
    
    def set_projection_type(self) -> None:
        """Method to set projection type for given observation."""

        projection_name = (
            self.component_manager.target_data.get('pointing', {})
            .get('projection', {})
            .get('name', "SIN")
        )

        projection_call = {
            "SIN": plane_to_sphere_sin,
            "ARC": plane_to_sphere_arc,
            "TAN": plane_to_sphere_tan,
            "CAR": plane_to_sphere_car,
            "SSN": plane_to_sphere_ssn,
            "STG": plane_to_sphere_stg,
        }

        self.logger.debug("Projection name: %s", projection_name)
        self.component_manager.projection_call = projection_call[projection_name]
    
    def set_reference_frame_handler(
            self, reference_frame_handler: str
    ) -> None:
        """Set the reference frame handler used for coordinate parsing.

        Args:
            reference_frame_handler: Name of the reference frame handler to use
                (e.g. 'tle', 'special', 'altaz', 'icrs'). Case-insensitive.

        Raises:
            KeyError: If the provided handler name is not recognised.
        """

        FRAME_HANDLERS = {
            "tle": self.handle_tle,
            "special": self.handle_special,
            "altaz": self.handle_altaz,
            "icrs": self.handle_icrs,
        }
        key = reference_frame_handler.lower()
        if key not in FRAME_HANDLERS:
            raise KeyError(
                f"Unknown reference frame handler: {reference_frame_handler}"
            )
        self.reference_frame_handler = FRAME_HANDLERS[key]
    
    def handle_tle(self, x_offset: float, y_offset: float, timestamp: str) -> List[float]:
        """Handle a TLE reference frame: compute Az/El for the TLE target.

        Args:
            x_offset: Offset along the x-axis in arcseconds.
            y_offset: Offset along the y-axis in arcseconds.
            timestamp: UTC timestamp string for the observation.

        Returns:
            List[float]: [Azimuth (deg), Elevation (deg)] after applying offsets
                and refraction correction.
        """

        self.logger.info(">>>>>>>>>.. %s", self.target)
        radec = self.target.radec(timestamp)
        self.logger.info(">>>>>>>>>.. %s", radec)
        return self.converter.apply_offset_and_get_azel_from_icrs(
            radec.ra.rad, radec.dec.rad, x_offset, y_offset, timestamp
        )

    def handle_special(self, x_offset: float, y_offset: float, timestamp: str) -> List[float]:
        """Handle a special (non-sidereal) target: compute Az/El.

        Args:
            x_offset: Offset along the x-axis in arcseconds.
            y_offset: Offset along the y-axis in arcseconds.
            timestamp: UTC timestamp string for the observation.

        Returns:
            List[float]: [Azimuth (deg), Elevation (deg)] after applying offsets
                and refraction correction.
        """

        radec = self.target.radec(timestamp)
        return self.converter.apply_offset_and_get_azel_from_icrs(
            radec.ra.rad, radec.dec.rad, x_offset, y_offset, timestamp
        )
    
    def handle_altaz(self, x_offset: float, y_offset: float, timestamp: str) -> List[float]:
        """Handle an alt/az reference: apply offsets in the alt/az plane.

        Args:
            x_offset: Offset along the x-axis in arcseconds.
            y_offset: Offset along the y-axis in arcseconds.
            timestamp: UTC timestamp string for the observation.

        Returns:
            List[float]: [Azimuth (deg), Elevation (deg)] after applying offsets
                and refraction correction.
        """

        return self.converter.apply_offset_and_get_azel_from_altaz(
            self.az, self.el, x_offset, y_offset, timestamp
        )
    
    def handle_icrs(self, x_offset: float, y_offset: float, timestamp: str) -> List[float]:
        """Handle an ICRS/RaDec reference: apply spherical offsets to ICRS coords.

        Args:
            x_offset: Offset along the x-axis in arcseconds.
            y_offset: Offset along the y-axis in arcseconds.
            timestamp: UTC timestamp string for the observation.

        Returns:
            List[float]: [Azimuth (deg), Elevation (deg)] after applying offsets
                and refraction correction.
        """

        return self.converter.apply_offset_and_get_azel_from_icrs(
            Angle(self.ra, u.deg).rad,
            Angle(self.dec, u.deg).rad,
            x_offset,
            y_offset,
            timestamp,
        )

    def set_target_and_start_process(self):
        """
        Generate program track table for normal scans.

        Args:
            scan_parameters (dict): A dictionary containing scan parameters.
            scan_id (str): A string representing the scan ID.

        Returns:
            dict: A dictionary containing the program track table.
        """
        # The below if checks the presence of target key in dish configure
        # input, if its present it checks what kind of reference frame
        #  it is for example, "special" or "icrs" and generates AzEl
        # accordingly
        try:
            self.build_data_for_observation()
            (
                self.component_manager.projection_name,
                self.component_manager.projection_alignment,
            ) = self.get_projection()
            if self.get_trajectory_name() == "fixed":
                (
                    self.component_manager.fixed_x_offset,
                    self.component_manager.fixed_y_offset,
                ) = self.get_fixed_trajectory_offsets()

            self.component_manager.start_track_table_calculation()

        except Exception as exception:
            self.logger.error("Exception: %s", exception)
            raise exception

    def get_trajectory_name(self):
        """Create Trajectory Object and set duration

        Returns:
            str: Name of the trajectory
        """

        trajectory = self.component_manager.target_data.get(
            'pointing', {}
        ).get("trajectory", {})
        trajectory_name = trajectory.get("name", "fixed").lower()
        return trajectory_name

    def get_time_offsets_and_set_cadence(self) -> list:
        """
        Get the time offsets for the scan.
        :return: A list of time offsets.
        """
        time_offsets = (
            self.component_manager.target_data.get("pointing", {})
            .get("trajectory", {})
            .get("attrs", {})
            .get("time_offsets", [])
        )
        if not time_offsets:
            scan_duration = self.component_manager.target_data.get(
                "tmc", {}
            ).get("scan_duration", 0)
            if not scan_duration:
                raise ValueError(
                    "Scan duration must be provided for trajectory scans."
                )
            self.cadence = (
                self.component_manager.track_table_update_rate
                / self.component_manager.program_track_table_size
            )
            time_offsets = list(np.arange(0, scan_duration, self.cadence))
        else:
            self.cadence = time_offsets[1] - time_offsets[0]
        self.logger.info(
            "Cadence for the scan is set to: %s seconds", self.cadence
        )
        return time_offsets

    def get_fixed_trajectory_offsets(self):
        """Get Fixed Trajectory Offsets

        Returns:
            tuple[float, float]: Tuple containing x and y offsets.
        """
        trajectory = self.component_manager.target_data.get(
            'pointing', {}
        ).get("trajectory", {})
        trajectory_attrs = trajectory.get("attrs", {}) or {'x': 0.0, 'y': 0.0}
        self.logger.debug(
            "Fixed trajectory offsets -> x: %s arcsec, y: %s arcsec",
            trajectory_attrs['x'],
            trajectory_attrs['y'],
        )
        return trajectory_attrs['x'], trajectory_attrs['y']

    def build_data_for_observation(self):
        """Build Data for Observation based
        on the target data provided in the dish configure input.

        Raises:
            InvalidTargetDataError: If target data is missing or invalid.
            Exception: If target construction fails.
        """
        target = False
        try:
            target_data = self.component_manager.target_data.get(
                "pointing", {}
            )
            target_dict = target_data.get("target", {})
            if target_dict:
                target_name = target_dict.get("target_name", "target")
                self.component_manager.target = target_name
                reference_frame = target_dict.get("reference_frame", "ICRS")
                if reference_frame.lower() == "special":
                    self.target = katpoint.Target(
                        f"{self.component_manager.target}, special"
                    )
                    self.set_reference_frame_handler("special")
                    target = True
                elif (
                    reference_frame.lower() == "icrs"
                    or reference_frame.lower() == "radec"
                ):
                    ra = target_dict.get("ra", "")
                    dec = target_dict.get("dec", "")
                    self.ra = Angle(ra, u.hourangle).deg
                    self.dec = Angle(dec, u.deg).deg
                    self.set_reference_frame_handler("icrs")
                    target = True
            field_dict = target_data.get("field", {})
            if field_dict:
                target_name = field_dict.get("target_name", "target")
                self.component_manager.target = target_name
                reference_frame = field_dict.get("reference_frame", "ICRS")
                if reference_frame.lower() == "special":
                    self.target = katpoint.Target(
                        f"{self.component_manager.target}, special"
                    )
                    self.set_reference_frame_handler("special")
                    target = True
                elif (
                    reference_frame.lower() == "icrs"
                    or reference_frame.lower() == "radec"
                ):
                    c1 = field_dict.get("attrs").get("c1", "")
                    c2 = field_dict.get("attrs").get("c2", "")
                    ra = Angle(c1 * u.deg)
                    ra_hms = ra.to_string(unit=u.hour, sep=':')
                    dec = Angle(c2 * u.deg)
                    dec_dms = dec.to_string(unit=u.deg, sep=':')
                    self.ra = ra_hms
                    self.dec = dec_dms
                    self.set_reference_frame_handler("icrs")
                    target = True
                elif reference_frame.lower() == "tle":
                    tle_line1 = field_dict.get("attrs", {}).get("line1", "")
                    tle_line2 = field_dict.get("attrs", {}).get("line2", "")
                    self.target = katpoint.Target(
                        f"{self.component_manager.target}, tle, {tle_line1}, {tle_line2}"
                    )
                    self.set_reference_frame_handler("tle")
                    target = True
                elif reference_frame.lower() == "altaz":
                    c1 = field_dict.get("attrs", {}).get("c1", "")
                    c2 = field_dict.get("attrs", {}).get("c2", "")
                    self.az = Angle(c1, u.deg).rad
                    self.el = Angle(c2, u.deg).rad
                    self.set_reference_frame_handler("altaz")
                    target = True
            if target:
                self.logger.info(
                    "Target set to: %s with reference frame: %s",
                    self.component_manager.target   ,
                    reference_frame,
                )
            else:
                raise InvalidTargetDataError()
        except Exception as exp:
            self.logger.exception(
                " Failed to set target for fixed/mosaic mapping "
                + "scan due to exception: %s",
                str(exp),
            )
            raise exp

    def extract_target_from_config(self):
        """
        Method to set the received ra and dec in the pointing
        groups field key
        """
        try:
            # Get target data with nested dicts
            target_data = self.component_manager.target_data.get(
                "pointing", {}
            )
            target_dict = target_data.get("target", {})
            field_dict = target_data.get("field", {}).get("attrs", {})
            ra, dec = target_dict.get("ra", ""), target_dict.get("dec", "")
            # Get c1 and c2 values
            c1, c2 = field_dict.get("c1", nan), field_dict.get("c2", nan)

            # Set target using the first non-empty value
            target = (
                ([ra, dec] if ra != "" and dec != "" else [])
                or ([c1, c2] if not (isnan(c1) or isnan(c2)) else [])
                or (target_dict.get("target_name"))
                or (target_data.get("field", {}).get("target_name", ""))
            )
            if target:
                self.component_manager.target = target
            else:
                raise InvalidTargetDataError()
        except Exception as exp:
            self.logger.exception(
                " Failed to set target for fixed/mosaic mapping "
                + "scan due to exception: %s",
                str(exp),
            )
            raise exp

    def setup_observation_target(self) -> None:
        """Set target required for mapping scan"""

        ra, dec = self.component_manager.target
        if isinstance(ra, float):
            ra = Angle(ra, unit=u.degree)
            dec = Angle(dec, unit=u.degree)
        self.ra_dec_target = Target.from_radec(ra, dec)
        self.ra_dec_target.antenna = self.component_manager.observer

    def get_projection(self) -> List[str | Any]:
        """This method returns the projection name and projection
        alignment

        :return: projection name, projection alignment
        :rtype: List
        """
        projection_name = (
            self.component_manager.target_data.get('pointing', {})
            .get('projection', {})
            .get('name', "SIN")
        )

        projection_alignment = (
            self.component_manager.target_data.get('pointing', {})
            .get('projection', {})
            .get('alignment', "altaz")
        )
        if projection_alignment.lower() == "icrs":
            projection_alignment = "radec"
        else:
            projection_alignment = "azel"
        self.logger.info(
            "Projection Name: %s, Alignment: %s",
            projection_name,
            projection_alignment,
        )
        return [projection_name.upper(), projection_alignment]

    def set_trajectory_and_duration(self):
        """Create Trajectory Object and set duration"""

        trajectory = self.component_manager.target_data.get(
            'pointing', {}
        ).get("trajectory", {})
        trajectory_name = trajectory.get("name", "fixed").lower()
        trajectory_attrs = trajectory.get("attrs", {}) or {'x': 0.0, 'y': 0.0}

        self.traj = TrajectoryName[trajectory_name](**trajectory_attrs)
        scan_duration = self.component_manager.target_data.get("tmc", {}).get(
            "scan_duration", 1.0
        )
        self.traj.set_scan_duration(scan_duration)

    def get_offset_in_rad(self, x: float, y: float) -> tuple:
        """Get the offset in radian

        Returns:
            tuple: offset in radian.
        """
        return Angle(x, u.arcsec).rad, Angle(y, u.arcsec).rad

    def get_radec_from_plane_to_sphere(self) -> Tuple[float, float]:
        """Convert plane coordinates to RA/Dec using spherical projection.

        Returns:
            List[str]: A list containing the calculated RA and Dec
            coordinates in string.
        """
        try:
            timestamp = katpoint.Timestamp()
            projection_name, projection_alignment = self.get_projection()
            self.set_trajectory_and_duration()
            x, y, _, _, _ = self.traj.posn(self.traj.start)
            x_rad, y_rad = self.get_offset_in_rad(x, y)
            with iers.earth_orientation_table.set(
                self.component_manager.iers_a
            ):
                ra, dec = self.ra_dec_target.plane_to_sphere(
                    x_rad,
                    y_rad,
                    timestamp,
                    projection_type=projection_name.upper(),
                    coord_system=projection_alignment,
                )
            updated_ra = Angle(ra, u.rad).deg
            updated_dec = Angle(dec, u.rad).deg
            self.logger.debug(
                "Updated ra and dec after plane to sphere %s, %s",
                updated_ra,
                updated_dec,
            )
            return updated_ra, updated_dec
        except Exception as exception:
            self.logger.exception("Exception: %s", exception)
            raise Exception(
                "Exception while setting Ra and Dec for mapping scan:"
                f" {exception}"
            ) from exception
