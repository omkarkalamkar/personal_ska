"""
SetOperateMode command class for DishLeafNode.
"""
import threading
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetOperateMode(DishLNCommand):
    """
    A class for DishLeafNode's SetOperateMode() command.

    SetOperateMode invokes SetOperateMode command on Dish Master device.

    """

    # pylint: disable=unused-argument
    def set_operate_mode(
        self,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """A method to invoke the SetOperateMode command.
        It sets the task_callback status according to command progress.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """

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

    # pylint: enable=unused-argument
    def do(self, argin=None):
        """
        Method to invoke SetOperateMode command on DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """
        ret_code, message = self.init_adapter()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        ret_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetOperateMode"
        )
        return ret_code, message
