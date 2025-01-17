"""This module contains GenerateProgramTrackTable implementation.
"""
import logging

from ska_tango_base.commands import FastCommand, ResultCode

from ska_dishln_pointing_device.dishlnpd_component_manager import (
    dishlnpd_component_manager as manager,
)
from ska_dishln_pointing_device.mapping_scan.point_mapping import (
    PointMappingScan,
)


class GenerateProgramTrackTable(FastCommand):
    """This class contains GenerateProgramTrackTrable implementation"""

    def __init__(
        self,
        logger: logging.Logger,
        component_manager: manager.DishlnPointingDataComponentManager,
    ):
        """Initialization.

        Args:
            logger (logging.Logger): Used for logging.
            component_manager (DishlnPointingDataComponentManager): Instance of
            DishlnPointingDataComponentManager.
        """
        super().__init__(logger)
        self.component_manager = component_manager

    def do(self, *args, **kwargs) -> None:
        """This method generates program track table."""
        try:
            self.logger.debug("Executing GenerateProgramTrackTable command.")
            with self.component_manager.track_thread_lock:
                self.component_manager.mapping_scan_event.clear()
            if (
                self.component_manager.target_data
                and "trajectory"
                not in self.component_manager.target_data["pointing"]
            ):
                self.component_manager.current_mapping_scan_obj = (
                    PointMappingScan(
                        pattern_name="point",
                        component_manager=self.component_manager,
                        logger=self.logger,
                    )
                )
                current_scan_obj = (
                    self.component_manager.current_mapping_scan_obj
                )
                current_scan_obj.set_target_and_start_process()
        except Exception as exception:
            self.logger.error(
                "Exception occurred in  GenerateProgramTrackTable"
                "command : %s",
                exception,
            )
            raise exception
        return ResultCode.STARTED, "ProgramTrackTable generation started"
