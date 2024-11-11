"""Module for generating program track table for normal scans"""

from __future__ import annotations

import threading
from logging import Logger

from ska_dishln_pointing_device.mapping_scan.mapping import BaseScanMapping


class NormalMappingScan(BaseScanMapping):
    """
     NormalMappingScan class inherits from BaseScanMapping class.
    It is used to generate program track table for normal scans.
    """

    def __init__(
        self,
        component_manager,
        logger: Logger,
    ):
        """
        Initialize the NormalMappingScan object.

        Args:
            dish_node (object): An object representing the dish node.
            logger (object, optional): An object for logging. Defaults to None.
        """
        super().__init__(component_manager=component_manager, logger=logger)

    def generate_program_track_table(self):
        """
        Generate program track table for normal scans.

        Args:
            scan_parameters (dict): A dictionary containing scan parameters.
            scan_id (str): A string representing the scan ID.

        Returns:
            dict: A dictionary containing the program track table.
        """

        if "target" in self.component_manager.target_data["pointing"]:
            if (
                self.component_manager.target_data["pointing"]["target"][
                    "reference_frame"
                ].lower()
                == "special"
            ):
                self.component_manager.target = (
                    self.component_manager.target_data["pointing"]["target"][
                        "target_name"
                    ]
                )
            else:
                self.component_manager.target = [
                    self.component_manager.target_data["pointing"]["target"][
                        "ra"
                    ],
                    self.component_manager.target_data["pointing"]["target"][
                        "dec"
                    ],
                ]
        else:
            self.component_manager.target = [
                self.component_manager.target_data["pointing"]["field"][
                    "attrs"
                ]["c1"],
                self.component_manager.target_data["pointing"]["field"][
                    "attrs"
                ]["c2"],
            ]
        track_thread = threading.Thread(
            target=self.component_manager.track_process
        )
        track_thread.start()
