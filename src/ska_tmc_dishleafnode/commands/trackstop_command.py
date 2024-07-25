"""TrackStop command class for Dishleafnode."""
from __future__ import annotations

import threading
from logging import Logger
from typing import Optional, Tuple

from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE


class TrackStop(DishLNCommand):
    """
    A class for Dishleafnode's TrackStop command. TrackStop command is
    inherited from DishLNCommand.

    This command invokes TrackStop command on Dish Master
    """

    # pylint: disable=unused-argument
    def trackstop(
        self: TrackStop,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """This is a long running method for TrackStop command, it
        executes the do hook, invoking TrackStop command on Dish Master

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
                result=(ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
            )

    # pylint: disable=arguments-differ
    def do(self: TrackStop) -> Tuple[ResultCode, str]:
        """
        Method to invoke TrackStop command on Dish Master.
        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
                "Adapter for device : %s is not found",
                self.component_manager.dish_dev_name,
=======
                "%s adapter not found ", self.component_manager.dish_dev_name
>>>>>>> 0f6bbb0 (improve loggers)
=======
                "Adapter for :%s not found",
=======
                "Adapter for device :%s not found",
>>>>>>> 642c346 (HM-505:Resolving minor logs)
                self.component_manager.dish_dev_name,
>>>>>>> 8a552ec (HM-505:Adding annotations)
            )
            return result_code, message
        # Stop the thread which started when Track command was invoked
        self.component_manager.set_track_process_event()
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "TrackStop"
            )

        return result_code[0], message[0]
