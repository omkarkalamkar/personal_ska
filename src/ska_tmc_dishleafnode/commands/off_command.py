"""On command class for Dishleafnode."""
from __future__ import annotations

import threading
from logging import Logger
from typing import Optional, Tuple

from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.enum import DishMode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE


class Off(DishLNCommand):
    """
    A class for Dishleafnode's Off command. Off command is
    inherited from DishLNCommand.

    This command invokes off command on Dish Master
    """

    # pylint: disable=unused-argument
    def invoke_off(
        self: Off,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        A method to invoke the Off command.
        It sets the task_callback status according to command progress.

        :param argin: Input JSON string
        :type argin: str
        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        :return: None
        :rtype: None
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)
        return_code, message = self.do()
        self.logger.debug(
            "Updating Task status with Result: %s ,Message: %s",
            ResultCode(return_code),
            message,
        )
        if return_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(return_code, message),
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
            )

    # pylint: disable=arguments-differ
    def do(self: Off) -> Tuple[ResultCode, str]:
        """
        Invokes StandbyFP and StandbyLP mode commands on dish master device
        after waiting for correct dish modes. First invokes and waits for
        completion of SetStandbyFPMode command, then invokes and waits for
        completion of SetStandbyLPMode command.


        Returns:
            Tuple[ResultCode, str]: Tuple of ResultCode and message.

        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.debug(
                "Adapter for : %s is not found ",
                self.component_manager.dish_dev_name,
            )
            return result_code, message
        if self.component_manager.dishMode in [
            DishMode.OPERATE,
            DishMode.STOW,
            DishMode.MAINTENANCE,
        ]:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "SetStandbyFPMode"
            )
            result: str = self.set_wait_for_dishmode(DishMode.STANDBY_FP)
            if result == "NOT_ACHIEVED":
                self.logger.debug(
                    "Timeout occurred while processing"
                    + "the SetStandbyFPMode "
                    + "command.",
                )
                return (
                    ResultCode.FAILED,
                    (
                        "Timeout occurred while invoking the SetStandbyFPMode "
                        + "command."
                    ),
                )
        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetStandbyLPMode"
        )
        result: str = self.set_wait_for_dishmode(DishMode.STANDBY_LP)
        if result == "NOT_ACHIEVED":
            self.logger.error(
                "Timeout occurred while processing the"
                + " SetStandbyLPMode Command."
            )
            return (
                ResultCode.FAILED,
                (
                    "Timeout occurred while invoking the SetStandbyLPMode "
                    + "command."
                ),
            )

        return result_code[0], message[0]
