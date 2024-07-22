"""Scan command class for Dishleafnode."""
<<<<<<< HEAD
=======
from __future__ import annotations
>>>>>>> 9708235 (HM-505: Resolving linting issues)

import threading
from logging import Logger
from typing import Optional

from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE


class Scan(DishLNCommand):
    """
    A class for Dishleafnode's Scan command. Scan command is
    inherited from DishLNCommand.

    This command invokes Scan command on Dish Master
    """

    # pylint: disable=unused-argument
    def scan(
<<<<<<< HEAD
        self,
=======
        self: Scan,
>>>>>>> 9708235 (HM-505: Resolving linting issues)
        argin: str,
        logger: Logger,
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
        :type task_callback: TaskCallbackType, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        :return: : None
        :rtype: None
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)
        result_code, message = self.do(argin)
        logger.info(message)
        if result_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(result_code, message),
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
            )

    # pylint: disable=signature-differs
<<<<<<< HEAD
    def do(self, argin: str):
=======
    def do(self: Scan, argin: str):
>>>>>>> 9708235 (HM-505: Resolving linting issues)
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
<<<<<<< HEAD
                "Adapter for device : %s is not found ",
                self.component_manager.dish_dev_name,
=======
                "%s adapter not found ", self.component_manager.dish_dev_name
>>>>>>> 0f6bbb0 (improve loggers)
            )
            return result_code, message

        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Scan", argin
            )

        return result_code[0], message[0]
