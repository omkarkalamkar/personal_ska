"""
SetOperateMode command class for DishLeafNode.
"""
from __future__ import annotations

import logging
import threading
from logging import Logger
from typing import Optional, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE

configure_logging()
LOGGER = logging.getLogger(__name__)


class SetOperateMode(DishLNCommand):
    """
    A class for DishLeafNode's SetOperateMode() command.

    SetOperateMode invokes SetOperateMode command on Dish Master device.

    """

    def __init__(
        self: SetOperateMode,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.task_callback = None

    # pylint: disable=unused-argument
    def set_operate_mode(
        self: SetOperateMode,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """A method to invoke the SetOperateMode command.
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
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)

        result_code, message = self.do()
        self.component_manager.setoperatemode_in_progress_id = message
        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(result_code, message),
                exception=message,
            )
        else:
            logger.info(
                "The SetOperateMode command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(
                    ResultCode.OK,
                    COMMAND_COMPLETION_MESSAGE,
                ),
            )

    # pylint: disable=arguments-differ
    def do(self: SetOperateMode) -> Tuple[ResultCode, str]:
        """
        Method to invoke SetOperateMode command on DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter for device : %s is not found",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "SetOperateMode"
            )
        return result_code[0], message[0]
