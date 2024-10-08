"""Track command class for Dishleafnode."""

from __future__ import annotations

import logging
import threading
import time
from logging import Logger
from typing import Optional, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import PointingState, TimeoutCallback

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class Track(DishLNCommand):
    """
    A class for Dishleafnode's Track command. Track command is
    inherited from DishLNCommand.

    This command invokes Track command on Dish Master
    """

    def __init__(
        self: Track,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.task_callback = None
        self.ra_value = ""
        self.dec_value = ""
        self.tracking_thread = None

    # pylint: disable=unused-argument
    def track(
        self: Track,
        argin: str,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """This is a long running method for Track command, it
        executes the do hook, invoking Track command on Dish Master

        :param argin: Input JSON string
        :type argin: str
        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        :return: : None
        :rtype: None
        """
        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback = TimeoutCallback(self.timeout_id, self.logger)
        # Indicate that the task has started
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        if self.component_manager.is_configure_command is False:
            self.set_command_id(__class__.__name__)
            self.component_manager.start_timer(
                self.timeout_id,
                self.component_manager.command_timeout,
                self.timeout_callback,
            )

        return_code, message = self.do(argin)
        self.component_manager.command_in_progress = "Track"
        logger.info("Message is: %s", message)
        if return_code in [
            ResultCode.FAILED,
            ResultCode.REJECTED,
            ResultCode.NOT_ALLOWED,
        ]:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(return_code, message),
                exception=message,
            )
        else:
            if self.component_manager.is_configure_command is False:
                self.start_tracker_thread(
                    "get_pointingstate",
                    [PointingState.TRACK],
                    task_abort_event,
                    self.timeout_id,
                    self.timeout_callback,
                    self.component_manager.command_id,
                    self.component_manager.long_running_result_callback,
                )

    def validate_json_argument(self: Track, input_argin: dict) -> tuple:
        """Validates the json argument"""
        target = input_argin.get("pointing", {}).get("target", {})
        ra_value = target.get("ra")
        dec_value = target.get("dec")
        if not ra_value or not dec_value:
            return (
                ResultCode.FAILED,
                "ra or dec value key is not present in the input json.",
            )

        return (ResultCode.OK, "")

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self: Track, argin: dict) -> Tuple[ResultCode, str]:
        """
        Method to invoke Track command on Dish Master.

        param argin: dict

        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter for device : %s is not found",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Track"
            )

        if result_code[0] == ResultCode.FAILED:
            return result_code[0], message[0]

        return result_code[0], message[0]
