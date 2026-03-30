"""This module contains StopProgramTrackTable implementation.
"""

import logging

from ska_tango_base.commands import FastCommand, ResultCode

from ska_dishln_pointing_device.dishlnpd_component_manager import (
    component_manager as manager,
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
            self.component_manager.stop_track_called.set()
            with self.component_manager.track_thread_lock:
                self.component_manager.mapping_scan_event.set()
            if (
                self.component_manager.track_table_thread
                and self.component_manager.track_table_thread.is_alive()
            ):
                # The track_table_thread is joined with a short timeout to
                # prevent the Stop command from triggering a Tango timeout
                self.logger.info("Event set")
                # self.component_manager.track_table_thread.join(timeout=1.0)
            self.component_manager.update_pointing_program_track_table([])
            self.component_manager.current_mapping_scan_obj = None
            self.logger.info(
                "StopProgramTrackTable command executed successfully"
                + " on %s",
                self.component_manager.dishln_pointing_device_name,
            )
            self.component_manager.stop_track_called.clear()
        except Exception as exception:
            self.logger.exception(
                "Exception occurred in StopProgramTrackTable command "
                "on %s, Exception: %s",
                self.component_manager.dishln_pointing_device_name,
                str(exception),
            )
            raise exception
        return ResultCode.OK, "Command Completed"
