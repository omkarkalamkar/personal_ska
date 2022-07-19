"""
SetStandbyFPMode command class for DishLeafNode.
"""
import threading
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetStandbyFPMode(DishLNCommand):
    """
    A class for DishLeafNode's SetStandbyFPMode() command.

    Invokes SetStandbyFPMode (i.e. Full Power State) command on DishMaster.

    """

    def check_allowed(self):
        """
        Checks whether this command is allowed. It checks that the device is
        in the right state to execute this command and that all the component
        needed for the operation are not unresponsive

        :return: True if this command is allowed

        :rtype: boolean

        """
        self.check_op_state(__class__.__name__)
        return True

    def set_standby_fp_mode(
        self,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """This is a long running method

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)

        ret_code, message = self.do()  # Fire and forget

        logger.info(message)

        if ret_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.FAILED,
                result=ResultCode.FAILED,
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode.OK,
            )

        # Periodically check that tasks have not been ABORTED
        if task_abort_event.is_set():
            # Indicate that the task has been aborted
            task_callback(
                status=TaskStatus.ABORTED,
                result="SetStandbyFPMode command task is aborted",
            )
        else:
            logger.info("Task_abort_event is not set")
            return

    def do(self, argin=None):
        """
        Method to invoke SetStandbyFPMode command on DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """

        ret_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetStandbyFPMode"
        )
        return ret_code, message
