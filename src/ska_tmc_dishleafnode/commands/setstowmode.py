"""
SetStowMode command class for DishLeafNode.
"""
import threading
from typing import Any, Callable, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand


class SetStowMode(DishLNCommand):
    """
    A class for DishleafNode's SetStowMode() command.

    SetStowMode command on DishLeafNode enables the telescope to perform
    further operations and observations. It Invokes SetStowMode command on
    Dish Leaf Node device.
    """

    # pylint: disable=unused-argument
    def set_stow_mode(
        self,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """A method to invoke the SetStowMode command.
        It sets the task_callback status according to command progress.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """

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
            logger.info(
                "The SetStowMode command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(result_code),
            )

    # pylint: enable=unused-argument
    def do(self, argin: Optional[Any] = None) -> Tuple[ResultCode, str]:
        """
        Method to invoke SetStowMode command on DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.info(
                "%s adapter not found ", self.component_manager.dish_dev_name
            )
            return result_code, message

        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetStowMode"
        )

        return result_code[0], message[0]
