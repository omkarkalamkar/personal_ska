"""Track command class for Dishleafnode."""

import datetime
import threading
import time
from datetime import timezone
from logging import Logger
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class Track(DishLNCommand):
    """
    A class for Dishleafnode's Track command. Track command is
    inherited from DishLNCommand.

    This command invokes Track command on Dish Master
    """

    # pylint: disable=unused-argument
    def track(
        self,
        argin: str,
        logger: Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:

        """This is a long running method for Track command, it
        executes the do hook, invoking Track command on Dish Master

        :param argin: Input JSON string
        :type argin : str
        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)
        return_code, message = self.do(argin)
        logger.info(message)
        if return_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=return_code,
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=return_code,
            )

    def validate_json_argument(self, input_argin: dict) -> tuple:
        """Validates the json argument"""
        target = input_argin.get("pointing", {}).get("target", {})
        ra_value = target.get("ra")
        dec_value = target.get("dec")
        if not ra_value or not dec_value:
            return self.generate_command_result(
                ResultCode.FAILED,
                "ra or dec value key is not present in the input json.",
            )

        return (ResultCode.OK, "")

    # pylint: disable=W0201
    def do(self, argin=None):
        """
        Method to invoke Track command on Dish Master.

        param argin: dict

        return:
            (ResultCode, str)
        """
        return_code, message = self.init_adapter()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.ra_value = argin["pointing"]["target"]["ra"]
        self.dec_value = argin["pointing"]["target"]["dec"]
        self.track_on_dish = False
        self.component_manager.el_limit = True
        self.component_manager.event_track_time.clear()

        # Start pointing calculations in a Track Thread
        self.tracking_thread = threading.Thread(
            None,
            self.component_manager.track_thread,
            "DishLeafNode",
            args=(self.ra_value, self.dec_value, self),
        )
        self.tracking_thread.start()
        radec_value = f"{self.ra_value}, {self.dec_value}"
        self.logger.info(
            "Track command ignores RA dec coordinates passed in: %s. "
            "Uses coordinates from Configure command instead.",
            radec_value,
        )

        return return_code, message
