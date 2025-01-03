"""This module contains StopProgramTrackTable implementation.
"""

import logging

from ska_tango_base.commands import FastCommand, ResultCode

from ska_dishln_pointing_device.dishlnpd_component_manager import (
    dishlnpd_component_manager as manager,
)


class StopProgramTrackTable(FastCommand):
    """This class contains StopProgramTrackTrable implementation"""

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
        """This method stops program track table generation."""
        try:
            self.logger.info("Executing StopProgramTrackTable command.")
            with self.component_manager.track_thread_lock:
                self.component_manager.mapping_scan_event.set()
            self.logger.info(
                "StopProgramTrackTable command executed successfully"
            )
            self.component_manager.update_program_track_table([])
        except Exception as exception:
            self.logger.error(
                "Exception occurred in StopProgramTrackTable command : %s",
                exception,
            )
            raise exception
        return ResultCode.OK, "Command Completed"
