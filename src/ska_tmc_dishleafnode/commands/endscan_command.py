"""EndScan command class for Dishleafnode."""

import threading
from logging import Logger
from typing import Optional

from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand


class EndScan(DishLNCommand):
    """
    A class for Dishleafnode's EndScan command. EndScan command is
    inherited from DishLNCommand.

    This command sets scanID attribute of Dish Master to empty string.
    """

    # pylint: disable=unused-argument
    def endscan(
        self,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """This is a method for long running command EndScan command, it
        executes the do hook, to set scanID attribute of Dish Master to empty
        string.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)
        result_code, message = self.do()
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
                result=(ResultCode.OK, "Command Completed"),
            )

    # pylint: disable=arguments-differ
    def do(self):
        """
        Method to set scanID attribute of Dish Master to empty string.

        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.info(
                "Error while creating adapter %s",
                self.component_manager.dish_dev_name,
            )
            return result_code, message
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "EndScan"
            )
        return result_code[0], message[0]
