"""
This module provides an implementation of the Dish Leaf Node
pointing device component manager.
"""

from logging import Logger

from ska_tmc_common.tmc_component_manager import BaseTmcComponentManager


class DishlnPointingDataComponentManager(BaseTmcComponentManager):
    """
    A component manager for The Dish leaf node pointing device component.
    """

    # pylint: disable=unused-argument
    def __init__(self, logger: Logger):
        """
        Initialise a new ComponentManager instance.

        :param logger: a logger for this component manager
        :param dishln_pointing_device_name: name of the dish
            pointing device
        """

        super().__init__(logger)
        self.logger = logger
