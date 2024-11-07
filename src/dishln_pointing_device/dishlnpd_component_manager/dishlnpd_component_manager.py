"""
This module provides an implementation of the Dish Leaf Node
pointing device component manager.
"""

import threading
from logging import Logger
from typing import Callable

from ska_tmc_common.tmc_component_manager import BaseTmcComponentManager


class DishlnPointingDataComponentManager(BaseTmcComponentManager):
    """
    A component manager for The Dish leaf node pointing device component.
    """

    # pylint: disable=unused-argument
    def __init__(
        self,
        logger: Logger,
        update_pointing_program_track_table_callback: Callable,
    ):
        """
        Initialise a new ComponentManager instance.

        :param logger: a logger for this component manager
        :param dishln_pointing_device_name: name of the dish
            pointing device
        """

        super().__init__(logger)
        self.logger = logger
        self.pointing_program_track_table: dict = {}
        self.update_pointing_program_track_table_callback = (
            update_pointing_program_track_table_callback
        )
        self.__target_data: list | str | None = None
        # This event can be used by on going process to change the offset
        # and clear the event for next usage.
        self.set_change_pointing_event = threading.Event()

    @property
    def target_data(self):
        """This method is used to view target data."""
        return self.__target_data

    @target_data.setter
    def target_data(self, data: str):
        """This method is used to update target data.

        Args:
            data (str): pointing data from configure command.
        """
        try:
            self.__target_data = data
        except Exception as exception:
            self.logger.error(
                "Writing of target data failed due to : %s", exception
            )

    def generate_program_track_table(self):
        """This method generates the program track table."""
        if self.update_pointing_program_track_table_callback:
            self.update_pointing_program_track_table_callback(
                self.pointing_program_track_table
            )

    def stop_program_track_table(self):
        """This method stops the generation of track table."""
