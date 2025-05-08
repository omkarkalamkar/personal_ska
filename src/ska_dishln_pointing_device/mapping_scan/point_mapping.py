"""Module for generating program track table for normal scans"""

from __future__ import annotations

from logging import Logger

from ska_dishln_pointing_device.mapping_scan.mapping import BaseScanMapping


class FixedMappingScan(BaseScanMapping):
    """
    FixedMappingScan class inherits from BaseScanMapping class.
    It is used to generate program track table for normal scans.
    """

    def __init__(
        self,
        pattern_name: str,
        component_manager,
        logger: Logger,
    ):
        """
        Initialize the FixedMappingScan object.
        :param dish_node (object): An object representing the dish node.
        :param logger (object, optional): An object for logging.
        """
        super().__init__(
            pattern_name=pattern_name,
            component_manager=component_manager,
            logger=logger,
        )
