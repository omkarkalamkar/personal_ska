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
        is_configure_command=False,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.is_configure_command = is_configure_command

    # pylint: disable=unused-argument
    def set_operate_mode(
        self: SetOperateMode,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """A method to invoke the SetOperateMode command.

        :return: A tuple containing the result code and a message.
        :rtype: Tuple[ResultCode, str]
        """
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        if self.is_configure_command is False:
            self.set_command_id(__class__.__name__)
            self.component_manager.start_timer(
                self.timeout_id,
                self.component_manager.command_timeout,
                self.timeout_callback,
            )

        result_code, message = self.do()
        self.component_manager.command_in_progress = "SetOperateMode"
        if result_code in [
            ResultCode.FAILED,
            ResultCode.REJECTED,
            ResultCode.NOT_ALLOWED,
        ]:
            self.update_task_status(
                result=(ResultCode.FAILED, message), exception=message
            )
        else:
            if self.is_configure_command is False:
                self.start_tracker_thread(
                    "get_set_operate_mode_result_code",
                    [ResultCode.OK],
                    task_abort_event,
                    self.timeout_id,
                    self.timeout_callback,
                    self.component_manager.command_id,
                    self.component_manager.long_running_result_callback,
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
