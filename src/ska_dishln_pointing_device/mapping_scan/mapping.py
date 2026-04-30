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

from ska_dishln_pointing_device.mapping_scan.utils import (
    InvalidTargetDataError,
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
        self.ra = None
        self.dec = None
        self.az = None
        self.el = None

    def set_projection_data(self) -> None:
        """Method to set projection type for given observation."""

        projection_name = (
            self.component_manager.target_data.get('pointing', {})
            .get('projection', {})
            .get('name', "SIN")
        ).upper()

        projection_alignment = (
            self.component_manager.target_data.get('pointing', {})
            .get('projection', {})
            .get('alignment', "icrs")
        ).lower()

        if projection_alignment not in ["icrs", "altaz"]:
            raise KeyError(
                f"Unknown projection alignment: {projection_alignment}"
            )

        if projection_name not in katpoint.plane_to_sphere:
            raise KeyError(f"Unknown projection type: {projection_name}")

        if projection_alignment == "icrs":
            projection_alignment = "radec"
        else:
            projection_alignment = "azel"

        self.component_manager.plane_to_sphere_handler = (
            katpoint.plane_to_sphere[projection_name.upper()]
        )
        self.component_manager.projection_alignment = projection_alignment
        self.logger.info(
            "Projection Name: %s, Alignment: %s",
            projection_name,
            projection_alignment,
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
                elif (
                    reference_frame.lower() == "icrs"
                    or reference_frame.lower() == "radec"
                ):
                    ra = target_dict.get("ra", "")
                    dec = target_dict.get("dec", "")
                    self.target = katpoint.Target(
                        f"{self.component_manager.target}, radec, {ra}, {dec}"
                    )
            field_dict = target_data.get("field", {})
            if field_dict:
                self.component_manager.target = field_dict.get(
                    "target_name", "target"
                )
                reference_frame = field_dict.get("reference_frame", "ICRS")
                if reference_frame.lower() == "special":
                    self.target = katpoint.Target(
                        f"{self.component_manager.target}, special"
                    )
                elif (
                    reference_frame.lower() == "icrs"
                    or reference_frame.lower() == "radec"
                ):
                    c1 = field_dict.get("attrs").get("c1", "")
                    c2 = field_dict.get("attrs").get("c2", "")
                    self.target = katpoint.Target(
                        f"{self.component_manager.target}, radec, {c1}, {c2}"
                    )
                elif reference_frame.lower() == "tle":
                    tle_line1 = field_dict.get("attrs", {}).get("line1", "")
                    tle_line2 = field_dict.get("attrs", {}).get("line2", "")
                    self.target = katpoint.Target(
                        f"{self.component_manager.target}, tle,"
                        f" {tle_line1}, {tle_line2}"
                    )
                elif reference_frame.lower() == "altaz":
                    c1 = field_dict.get("attrs", {}).get("c1", "")
                    c2 = field_dict.get("attrs", {}).get("c2", "")
                    self.target = katpoint.Target(
                        f"{self.component_manager.target}, azel, {c1}, {c2}"
                    )
            if self.target:
                self.logger.info(
                    "Target set to: %s with reference frame: %s",
                    self.target,
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
