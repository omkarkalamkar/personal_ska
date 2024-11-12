"""This module contains GenerateProgramTrackTable implementation.
"""
import logging

from ska_tango_base.commands import FastCommand, ResultCode

from ska_dishln_pointing_device.dishlnpd_component_manager import (
    dishlnpd_component_manager as manager,
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
        return ResultCode.STARTED, "Generation Started"
