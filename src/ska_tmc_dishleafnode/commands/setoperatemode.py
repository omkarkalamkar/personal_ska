"""
SetOperateMode command class for DishLeafNode.
"""
from __future__ import annotations

import logging
import threading
import time
from logging import Logger
from typing import Callable, Optional, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import DishMode, TimeoutCallback, TimeoutState

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

# from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE

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
        # self.timekeeper = TimeKeeper(
        #     self.component_manager.command_timeout, logger
        # )
        self.timeout_id: str = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback: Callable[
            [str, TimeoutState], Optional[ValueError]
        ] = TimeoutCallback(self.timeout_id, self.logger)
        self.task_callback: TaskCallbackType

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
        if self.component_manager.is_configure_command is False:
            logger.info(
                "Configure flag: %s",
                self.component_manager.is_configure_command,
            )
            self.set_command_id(__class__.__name__)
            self.component_manager.start_timer(
                self.timeout_id,
                self.component_manager.command_timeout,
                self.timeout_callback,
            )
        else:
            logger.info(
                " SetOperateMode is invoked as part of Configure"
                + " command. The configure timer is utilised."
            )
        result_code, message = self.do()
        self.component_manager.setoperatemode_in_progress_id = message
        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(result_code, message),
                exception=message,
            )
        else:
            if self.component_manager.is_configure_command is False:
                logger.info(
                    "Configure flag: %s",
                    self.component_manager.is_configure_command,
                )
                self.start_tracker_thread(
                    "get_dishmode",
                    [DishMode.OPERATE],
                    task_abort_event,
                    self.timeout_id,
                    self.timeout_callback,
                    self.component_manager.command_id,
                    self.component_manager.long_running_result_callback,
                )
            else:
                logger.info(
                    " SetOperateMode is invoked as part of Configure"
                    + " command. The command status is monitored in "
                    + "Configure command tracker thread."
                )
            # logger.info(
            #     "The SetOperateMode command is invoked successfully on %s",
            #     self.dish_master_adapter.dev_name,
            # )
            # self.task_callback(
            #     status=TaskStatus.COMPLETED,
            #     result=(
            #         ResultCode.OK,
            #         COMMAND_COMPLETION_MESSAGE,
            #     ),
            # )

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
