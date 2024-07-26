"""
SetStowMode command class for DishLeafNode.
"""
from __future__ import annotations

import threading
from logging import Logger
from typing import Optional, Tuple

from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE


class SetStowMode(DishLNCommand):
    """
    A class for DishleafNode's SetStowMode() command.

    SetStowMode command on DishLeafNode enables the telescope to perform
    further operations and observations. It Invokes SetStowMode command on
    Dish Leaf Node device.
    """

    # pylint: disable=unused-argument
    def set_stow_mode(
        self: SetStowMode,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """A method to invoke the SetStowMode command.
        It sets the task_callback status according to command progress.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        :return: : None
        :rtype: None
        """

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
            logger.info(
                "The SetStowMode command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
            )

    # pylint: disable=arguments-differ
    def do(self: SetStowMode) -> Tuple[ResultCode, str]:
        """
        Method to invoke SetStowMode command on DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
                "Adapter for device : %s is not found ",
                self.component_manager.dish_dev_name,
=======
                "%s adapter not found ", self.component_manager.dish_dev_name
>>>>>>> 0f6bbb0 (improve loggers)
=======
                "Adapter for device :%s not found ", self.component_manager.dish_dev_name
>>>>>>> 642c346 (HM-505:Resolving minor logs)
=======
                "Adapter for device :%s not found ",
=======
                "Adapter for device : %s is not found ",
>>>>>>> 6d43fa8 (HM-505:resolving review ccomments)
                self.component_manager.dish_dev_name,
>>>>>>> 506451f (HM-505:Resolved lint issue)
            )
            return result_code, message
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "SetStowMode"
            )

        return result_code[0], message[0]
