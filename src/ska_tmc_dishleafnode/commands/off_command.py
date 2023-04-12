"""On command class for Dishleafnode."""

import threading
from logging import Logger
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.enum import DishMode

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class Off(DishLNCommand):
    """
    A class for Dishleafnode's ON command. On command is
    inherited from DishLNCommand.

    This command invokes on command on Dish Master
    """

    # pylint: disable=unused-argument
    def invoke_off(
        self,
        logger: Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:

        """This is a long running method for On command, it
        executes the do hook, invoking Off command on Dish Master

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
        return_code, message = self.do()
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

    def do(self, argin=None):
        """
        Method to invoke On command on Dish Master.

        param argin:
            None

        return:
            (ResultCode, str)
        """
        return_code, message = self.init_adapter()
        if return_code == ResultCode.FAILED:
            return return_code, message

        return_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetStandbyFPMode"
        )
        result = self.set_wait_for_dishmode(DishMode.STANDBY_FP)
        if not result:
            return (
                ResultCode.FAILED,
                "Timeout occured while invoking the SetStandbyFPMode Command.",
            )
        return_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetStandbyLPMode"
        )
        result = self.set_wait_for_dishmode(DishMode.STOW)
        if not result:
            return (
                ResultCode.FAILED,
                "Timeout occured while invoking the SetStandbyLPMode Command.",
            )
        return return_code, message
