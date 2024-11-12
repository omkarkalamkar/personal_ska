"""This module provides base class for the mappings/patterns"""

import threading
from logging import Logger


class BaseScanMapping:
    """Base class for all scan mappings/patterns"""

    def __init__(
        self,
        pattern_name: str,
        component_manager,
        logger: Logger,
    ) -> None:
        self.pattern_name = pattern_name
        self.target = None
        self.component_manager = component_manager
        self.logger = logger

    def set_target_and_start_process(self):
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
                self.target = self.component_manager.target_data["pointing"][
                    "target"
                ]["target_name"]
            else:
                self.target = [
                    self.component_manager.target_data["pointing"]["target"][
                        "ra"
                    ],
                    self.component_manager.target_data["pointing"]["target"][
                        "dec"
                    ],
                ]
        else:
            self.target = [
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
