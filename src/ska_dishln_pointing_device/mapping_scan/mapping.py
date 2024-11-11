"""This module provides base class for the mappings/patterns"""

from logging import Logger


class BaseScanMapping:
    """Base class for all scan mappings/patterns"""

    def __init__(
        self,
        component_manager,
        logger: Logger,
    ) -> None:
        self.component_manager = component_manager
        self.logger = logger

    def generate_program_track_table(self) -> None:
        """Generate program track table"""
        raise NotImplementedError(
            "generate_program_track_table must be implemented"
        )
