"""This module provides class for the fixed mapping scan"""

from logging import Logger

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
                "Provided Ra and Dec are %s, %s",
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
