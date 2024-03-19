"""EndScan command class for Dishleafnode."""

import threading
from logging import Logger
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand


class EndScan(DishLNCommand):
    """
    A class for Dishleafnode's EndScan command. EndScan command is
    inherited from DishLNCommand.

    This command invokes EndScan command on Dish Master
    """

    # pylint: disable=unused-argument
    def endscan(
        self,
        logger: Logger,
        task_callback: Callable,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """This is a long running method for EndScan command, it
        executes the do hook, invoking EndScan command on Dish Master

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
                result=ResultCode(result_code),
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(result_code),
            )

    # pylint: disable=arguments-differ
    def do(self):
        """
        Method to invoke EndScan command on Dish Master.

        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.info("%s adapter not found ", self.component_manager.dish_dev_name)
            return result_code, message
        result_code, message = self.call_adapter_method(
            "Dish Master",
            self.dish_master_adapter,
            "EndScan",
        )
        self.logger.info(
            "The scanID attribute of dish master is %s", self.dish_master_adapter.scanID
        )
        self.dish_master_adapter.scanID = ""
        self.logger.info(
            "The updated scanID attribute of dish master is %s", self.dish_master_adapter.scanID
        )
        return result_code[0], message[0]
