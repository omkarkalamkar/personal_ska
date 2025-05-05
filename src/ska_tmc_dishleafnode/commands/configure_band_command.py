"""ConfigureBand command class for Dishleafnode."""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import TimeKeeper, TimeoutCallback, TimeoutState
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import ADJUST_TIMEOUT

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
        is_configure_command: bool = False,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.is_configure_command = is_configure_command
        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback: Callable[
            [str, TimeoutState], Optional[ValueError]
        ] = TimeoutCallback(self.timeout_id, self.logger)
        if self.is_configure_command:
            self.timekeeper = TimeKeeper(
                self.component_manager.command_timeout - ADJUST_TIMEOUT, logger
            )
        else:
            self.timekeeper = TimeKeeper(
                self.component_manager.command_timeout, logger
            )
        self.configure_band_id = self.timeout_id
        if self.component_manager.is_configure_command:
            self.component_manager.configure_command_timer_list.append(
                self.timekeeper
            )

    # pylint: disable=unused-argument
    @timeout_tracker
    @error_propagation_tracker(
        "get_configure_band_result_code", [ResultCode.OK]
    )
    def configure_band(
        self: ConfigureBand,
        argin: str,
        **kwargs,
    ) -> Tuple[ResultCode, str]:
        """This is a long running method for ConfigureBand command, it
        executes the do hook, invoking ConfigureBand command on Dish Master

        :param argin: string containing band to be configured
        :type argin: str
        :return: : (ResultCode, str)
        :rtype: Tuple
        """
        self.component_manager.command_id = self.configure_band_id
        # Indicate that the task has started
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        if self.is_configure_command is False:
            self.set_command_id(__class__.__name__)
        else:
            self.component_manager.command_in_progress = "Configure"

        return self.do(argin)

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self: ConfigureBand, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke ConfigureBand command on Dish Master.

        param argin: str

        return:
            (ResultCode, str)
        """
        self.logger.debug(
            "Command ID: %s | Input argument for ConfigureBand command is: %s",
            str(self.component_manager.command_id),
            argin,
        )
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.debug(
                "Command ID: %s | Failed to find adapter for device: %s",
                str(self.component_manager.command_id),
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        command_name: str = f"ConfigureBand{argin}"
        self.logger.debug(
            "Command ID: %s | Preparing to execute command: %s",
            str(self.component_manager.command_id),
            command_name,
        )
        self.logger.debug(
            "Command ID: %s | Command: %s will be executed on %s",
            str(self.component_manager.command_id),
            command_name,
            self.component_manager.dish_dev_name,
        )
        with self.component_manager.tango_operation_execution_lock:
            self.logger.debug(
                "Command ID: %s | Acquired tango lock",
                str(self.component_manager.command_id),
            )
            result_code, message = self.call_adapter_method(
                "Dish Master",
                self.dish_master_adapter,
                command_name,
                True,
            )
            if ResultCode(result_code[0]) is ResultCode.QUEUED:
                # Append command unique id
                self.component_manager.command_unique_id_dict[
                    command_name
                ] = message[0]

            self.logger.info(
                "Command ID: %s |"
                + " %s Command executed on %s "
                + "with Result: %s, Message: %s",
                str(self.component_manager.command_id),
                command_name,
                self.component_manager.dish_dev_name,
                ResultCode(result_code[0]),
                message,
            )

            self.logger.debug(
                "Command ID: %s | Released tango lock",
                str(self.component_manager.command_id),
            )

        if result_code[0] == ResultCode.FAILED:
            return result_code[0], message[0]

        return result_code[0], message[0]
