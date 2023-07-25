"""TrackStop command class for Dishleafnode."""

import threading
from logging import Logger
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


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
        return_code, message = self.do()
        logger.info(message)
        if return_code[0] == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(return_code[0]),
                exception=str(message[0]),
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(return_code[0]),
            )

    def do(self, argin=None):
        """
        Method to invoke TrackStop command on Dish Master.
        return:
            (ResultCode, str)
        """
        return_code, message = self.init_adapter()
        if return_code == ResultCode.FAILED:
            return [return_code], [message]
        # Stop the thread which started when Track command was invoked
        self.component_manager.event_track_time.set()
        return_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "TrackStop"
        )
        if self.dish_master_adapter is None:
            return [return_code], [message]
        return return_code, message
