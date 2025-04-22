"""This module provides base class for the mappings/patterns"""

from logging import Logger
from typing import Tuple

import katpoint
from astropy import units as u
from astropy.coordinates import Angle
from astropy.utils import iers
from numpy import nan

from ska_dishln_pointing_device.mapping_scan.mapping import BaseScanMapping


class FixedMappingScan(BaseScanMapping):
    """Class for trajectory dishes in holography/mapping
    scans. The trajectory dishes does fixed scanning in
    mapping scans."""

    def __init__(
        self,
        pattern_name: str,
        component_manager,
        logger: Logger,
    ) -> None:
        super().__init__(
            pattern_name=pattern_name,
            component_manager=component_manager,
            logger=logger,
        )
        self.target: str | None = None
        self.component_manager = component_manager
        self.logger = logger
        self.main_target_dec = None
        self.main_target_ra = None
        self.ra_dec_target = None
        self.x_offset = 0.0
        self.y_offset = 0.0

    def set_offsets(self):
        """Set x and y Offset provided in target data"""
        if "trajectory" in self.component_manager.target_data["pointing"]:
            trajectory = self.component_manager.target_data["pointing"][
                "trajectory"
            ]
            x = float(trajectory['attrs']['x'])
            y = float(trajectory['attrs']['y'])
            self.x_offset, self.y_offset = (
                Angle(x, u.deg).rad,
                Angle(y, u.deg).rad,
            )
            self.logger.info("X %s and Y %s ", x, y)
            self.logger.info(
                "x offset %s and y offset %s updated",
                self.x_offset,
                self.y_offset,
            )

    def set_target_and_start_process(self):
        """
        Generate program track table for fixed mapping scans.
        """
        # The below if checks the presence of target key in dish configure
        # input, if its present it checks what kind of reference frame
        #  it is for example, "special" or "icrs" and generates AzEl
        # accordingly
        try:
            # The below code is for trajectory dishes in holography/mapping
            # scans. The trajectory dishes which are responsible for
            #  fixed offsets scanning in
            # mapping scans i.e x=0.0 and y=0.0 and projection as SIN
            # with projection alignment as ICRS
            if "field" in self.component_manager.target_data["pointing"]:
                self.extract_target_from_config()
                self.setup_observation_target()
            self.logger.info(
                "main ra %s and main dec %s",
                self.main_target_ra,
                self.main_target_dec,
            )
            self.component_manager.target = (
                self.get_radec_from_plane_to_sphere()
            )
            self.component_manager.start_track_table_calculation()

        except Exception as exception:
            self.logger.exception("Exception: %s", exception)
            raise Exception(
                "Exception while configuring fixed mapping scan:"
                f" {exception}"
            ) from exception

    def get_radec_from_plane_to_sphere(self) -> Tuple[float, float]:
        """Convert plane coordinates to RA/Dec using spherical projection.

        Returns:
            List[str]: A list containing the calculated RA and Dec
            coordinates in string.
        """
        try:
            timestamp = katpoint.Timestamp()
            az = nan
            el = nan
            projection_name, projection_alignment = self.get_projection()
            self.logger.info(
                "Calling plane to sphere with %s and %s",
                self.x_offset,
                self.y_offset,
            )
            with iers.earth_orientation_table.set(
                self.component_manager.iers_a
            ):
                az, el = self.ra_dec_target.plane_to_sphere(
                    self.x_offset,
                    self.y_offset,
                    timestamp,
                    projection_type=projection_name.upper(),
                    coord_system=projection_alignment.upper(),
                )
            return self.azel_to_radec(az, el, timestamp.to_string())
        except Exception as exception:
            self.logger.exception("Exception: %s", exception)
            raise Exception(
                "Exception while setting Ra and Dec for mapping scan:"
                f" {exception}"
            ) from exception
