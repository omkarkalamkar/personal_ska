"""This module provides base class for the mappings/patterns"""

from logging import Logger
from typing import Any, List, Tuple

from astropy import units as u
from astropy.coordinates import AltAz, Angle
from astropy.utils import iers
from katpoint import Target
from ska_trajectory.trajectory import TrajectoryName


class BaseScanMapping:
    """Base class for all scan mappings/patterns"""

    def __init__(
        self,
        pattern_name: str,
        component_manager,
        logger: Logger,
    ) -> None:
        self.pattern_name = pattern_name
        self.target: str | None = None
        self.component_manager = component_manager
        self.logger = logger
        self.main_target_ra = None
        self.main_target_dec = None
        self.ra_dec_target = None
        self.traj = None

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
            if (
                self.component_manager.target_data["pointing"]["target"][
                    "reference_frame"
                ].lower()
                == "special"
            ):
                self.component_manager.target = (
                    self.component_manager.target_data["pointing"]["target"][
                        "target_name"
                    ]
                )
            else:
                self.component_manager.target = [
                    self.component_manager.target_data["pointing"]["target"][
                        "ra"
                    ],
                    self.component_manager.target_data["pointing"]["target"][
                        "dec"
                    ],
                ]
            self.component_manager.start_track_table_calculation()
        except Exception as exception:
            self.logger.error("Exception: %s", exception)

    def extract_target_from_config(self):
        """
        Method to set the received ra and dec in the pointing
        groups field key
        """
        try:
            # set initial point as a target for track table generation
            self.main_target_ra = self.component_manager.target_data[
                "pointing"
            ]["field"]["attrs"]["c1"]
            self.main_target_dec = self.component_manager.target_data[
                "pointing"
            ]["field"]["attrs"]["c2"]
        except Exception as exp:
            self.logger.exception(
                "Exception while setting target for fixed/mosaic"
                " mapping scan %s",
                exp,
            )
            raise exp

    def setup_observation_target(self) -> None:
        """Set target required for mapping scan"""

        ra = self.main_target_ra
        dec = self.main_target_dec
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
        projection_name = self.component_manager.target_data['pointing'][
            'projection'
        ]['name']
        projection_alignment = self.component_manager.target_data['pointing'][
            'projection'
        ]['alignment']

        if projection_alignment.lower() == "icrs":
            projection_alignment = "radec"
        else:
            projection_alignment = "azel"
        return [projection_name, projection_alignment]

    def set_trajectory_and_duration(self):
        """Create Trajectory Object and set duration"""

        trajectory = self.component_manager.target_data["pointing"][
            "trajectory"
        ]
        self.traj = TrajectoryName[trajectory["name"].capitalize()](
            **trajectory["attrs"]
        )
        scan_duration = self.component_manager.target_data["tmc"][
            "scan_duration"
        ]
        self.traj.set_scan_duration(scan_duration)

    def azel_to_radec(
        self,
        az_value: float,
        el_value: float,
        timestamp: str,
    ) -> Tuple[float, float]:
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

        azel = AltAz(az=Angle(az_value, u.rad), alt=Angle(el_value, u.rad))

        target = Target.from_azel(
            azel.az,
            azel.alt,
        )

        # Preloading the IERS A chart for Astrop's usage.
        with iers.earth_orientation_table.set(self.component_manager.iers_a):
            ra_dec = target.radec(
                timestamp=timestamp, antenna=self.component_manager.observer
            )

            ra = Angle(ra_dec.ra, u.rad).deg
            dec = Angle(ra_dec.dec, u.rad).deg

        self.logger.debug(
            "After plane to sphere: The Right Ascension is : %s"
            " and the Declination is : %s ",
            ra,
            dec,
        )
        return ra, dec
