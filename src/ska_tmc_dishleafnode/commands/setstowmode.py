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
        self.logger.debug(
            "Command ID: %s | Updating task status with Result: %s"
            + " Message: %s",
            self.component_manager.command_id,
            result_code,
            message,
        )
        if result_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(result_code, message),
                exception=message,
            )
        else:
            logger.info(
                "Command ID: %s | "
                "SetStowMode command is invoked successfully on %s",
                message,
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
            self.logger.debug(
                "Command ID: %s | Adapter for : %s is not found ",
                message,
                self.component_manager.dish_dev_name,
            )
            return result_code, message
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "SetStowMode"
            )

        return result_code[0], message[0]
