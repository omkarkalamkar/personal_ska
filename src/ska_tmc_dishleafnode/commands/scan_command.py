"""Scan command class for Dishleafnode."""

import threading
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class Scan(DishLNCommand):
    """
    A class for Dishleafnode's Scan() command. Scan command is
    inherited from CspSLNCommand.

    This command invokes Scan command on Dish Leaf node
    """

    # pylint: disable=unused-argument
    def scan(
        self,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:

        """This is a long running method for Scan command, it
        executes do hook, invokes Scan command on Dishleafnode

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
        ret_code, message = self.do()
        logger.info(message)
        if ret_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode.FAILED,
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode.OK,
            )

    # pylint: disable=W0221
    def do(self) -> tuple:
        """

        Method to invoke Scan command on Dish Leaf Node

        :return: (ResultCode, message)
        :raises Exception: if the command execution is not successful
        """
        ret_code, message = self.init_adapter()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        ret_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "Scan"
        )

        return (ResultCode.OK, "")
