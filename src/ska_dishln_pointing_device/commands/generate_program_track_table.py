"""This module contains GenerateProgramTrackTable implementation.
"""
import logging

from ska_tango_base.commands import FastCommand, ResultCode

from ska_dishln_pointing_device.dishlnpd_component_manager import (
    dishlnpd_component_manager as manager,
)
from ska_dishln_pointing_device.mapping_scan.point_mapping import (
    FixedMappingScan,
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
                self.component_manager.stop_track_table_thread()
                self.component_manager.current_mapping_scan_obj = (
                    FixedMappingScan(
                        pattern_name="fixed",
                        component_manager=self.component_manager,
                        logger=self.logger,
                    )
                )
            current_scan_obj = self.component_manager.current_mapping_scan_obj
            current_scan_obj.set_target_and_start_process()
        except Exception as exception:
            self.logger.error(
                "Exception occurred in  GenerateProgramTrackTable"
                "command : %s",
                exception,
            )
            raise exception
        return ResultCode.STARTED, "ProgramTrackTable generation started"
