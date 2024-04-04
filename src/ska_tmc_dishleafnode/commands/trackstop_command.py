"""TrackStop command class for Dishleafnode."""

import threading
from logging import Logger
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand


class TrackStop(DishLNCommand):
    """
    A class for Dishleafnode's TrackStop command. TrackStop command is
    inherited from DishLNCommand.

    This command invokes TrackStop command on Dish Master
    """

    # pylint: disable=unused-argument
    def trackstop(
        self,
        logger: Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """This is a long running method for TrackStop command, it
        executes the do hook, invoking TrackStop command on Dish Master

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

    def do(self, argin=None):
        """
        Method to invoke TrackStop command on Dish Master.
        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.info("%s adapter not found ", self.component_manager.dish_dev_name)
            return result_code, message
        # Stop the thread which started when Track command was invoked
        self.component_manager.set_track_process_event()
        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "TrackStop"
        )

        return result_code[0], message[0]
