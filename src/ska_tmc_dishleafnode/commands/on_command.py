"""On command class for Dishleafnode."""

import threading
import time
from logging import Logger
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.enum import DishMode

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class On(DishLNCommand):
    """
    A class for Dishleafnode's ON command. On command is
    inherited from DishLNCommand.

    This command invokes on command on Dish Master
    """

    # pylint: disable=unused-argument
    def invoke_on(
        self,
        logger: Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:

        """This is a long running method for On command, it
        executes the do hook, invoking On command on Dish Master

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

    def set_wait_for_dishmode(self, dishmode: DishMode) -> bool:
        """Waits for transition of DishMode to the correct state."""
        start_time = time.time()
        elapsed_time = 0
        while elapsed_time < self.component_manager.timeout:
            if self.component_manager.dishMode == dishmode:
                break
            elapsed_time = time.time() - start_time
        if self.component_manager.dishMode == dishmode:
            return True
        return False

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
            "Dish Master", self.dish_master_adapter, "SetOperateMode"
        )
        result = self.set_wait_for_dishmode(DishMode.OPERATE)
        if not result:
            return (
                ResultCode.FAILED,
                "Timeout occured while invoking the SetOperateMode Command.",
            )
        return return_code, message
