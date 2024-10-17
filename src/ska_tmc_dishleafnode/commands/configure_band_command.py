"""ConfigureBand command class for Dishleafnode."""

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


class ConfigureBand(DishLNCommand):
    """
    A class for Dishleafnode's ConfigureBand command. ConfigureBand command is
    inherited from DishLNCommand.

    This command takes band as an input argument and invokes respective
    ConfigureBand{band} command on Dish Master
    """

    def __init__(
        self: ConfigureBand,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )

    # pylint: disable=unused-argument
    def configure_band(
        self: ConfigureBand,
        argin: str,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """This is a long running method for ConfigureBand command, it
        executes the do hook, invoking ConfigureBand command on Dish Master

        :param argin: string containing band to be configured
        :type argin: str
        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        :return: : None
        :rtype: None
        """
        # Indicate that the task has started
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        if self.component_manager.is_configure_command is False:
            self.set_command_id(__class__.__name__)
            self.component_manager.start_timer(
                self.timeout_id,
                self.component_manager.command_timeout,
                self.timeout_callback,
            )

        return_code, message = self.do(argin)
        self.component_manager.command_in_progress = "ConfigureBand"
        logger.info("Result and Message is: %s, %s", return_code, message)
        if return_code in [
            ResultCode.FAILED,
            ResultCode.REJECTED,
            ResultCode.NOT_ALLOWED,
        ]:
            self.update_task_status(
                result=(ResultCode.FAILED, message), exception=message
            )
        else:
            if self.component_manager.is_configure_command is False:
                self.start_tracker_thread(
                    "get_configure_band_result",
                    [ResultCode.OK],
                    task_abort_event,
                    self.timeout_id,
                    self.timeout_callback,
                    self.component_manager.command_id,
                    self.component_manager.long_running_result_callback,
                )

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self: ConfigureBand, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke ConfigureBand command on Dish Master.

        param argin: str

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

        command_name: str = f"ConfigureBand{argin}"
        self.logger.info("command_name: %s", command_name)
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master",
                self.dish_master_adapter,
                command_name,
                True,
            )

        if result_code[0] == ResultCode.FAILED:
            return result_code[0], message[0]

        return result_code[0], message[0]
