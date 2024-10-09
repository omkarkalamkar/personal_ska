"""Scan command class for Dishleafnode."""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import TimeoutCallback

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class Scan(DishLNCommand):
    """
    A class for Dishleafnode's Scan command. Scan command is
    inherited from DishLNCommand.

    This command invokes Scan command on Dish Master
    """

    def __init__(
        self: Scan,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )

    # pylint: disable=unused-argument
    def scan(
        self: Scan,
        argin: str,
        logger: logging.Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """This is a long running method for Scan command, it
        executes the do hook, invoking Scan command on Dish Master

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
        self.task_callback = task_callback
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)

        self.set_command_id(__class__.__name__)
        self.component_manager.start_timer(
            self.timeout_id,
            self.component_manager.command_timeout,
            self.timeout_callback,
        )

        result_code, message = self.do(argin)
        self.component_manager.command_in_progress = "Scan"
        logger.info(message)
        if result_code in [
            ResultCode.FAILED,
            ResultCode.REJECTED,
            ResultCode.NOT_ALLOWED,
        ]:
            logger.warning("Command failed with exception: %s", message)
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(result_code, message),
                exception=message,
            )
            self.component_manager.command_in_progress = ""
        else:
            logger.info(
                "The Scan command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )

            self.start_tracker_thread(
                "get_scan_result",
                [ResultCode.OK],
                task_abort_event,
                self.timeout_id,
                self.timeout_callback,
                self.component_manager.command_id,
                self.component_manager.long_running_result_callback,
            )

    # pylint: disable=signature-differs
    def do(self: Scan, argin: str):
        """
        Method to invoke Scan command on Dish Master.

        param argin:
            None

        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter for device : %s is not found ",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Scan", argin
            )

        return result_code[0], message[0]
