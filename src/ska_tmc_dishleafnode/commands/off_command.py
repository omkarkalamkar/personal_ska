"""On command class for Dishleafnode."""
<<<<<<< HEAD
=======
from __future__ import annotations
<<<<<<< HEAD
>>>>>>> 9708235 (HM-505: Resolving linting issues)
=======
>>>>>>> 9708235 (HM-505: Resolving linting issues)

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
<<<<<<< HEAD
<<<<<<< HEAD
        self,
=======
        self: Off,
>>>>>>> 9708235 (HM-505: Resolving linting issues)
=======
        self: Off,
>>>>>>> 9708235 (HM-505: Resolving linting issues)
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
        :return: : None
        :rtype: None
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)
        return_code, message = self.do()
        logger.info(message)
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
                "Adapter for device : %s is not found ",
                self.component_manager.dish_dev_name,
=======
                "%s adapter not found ", self.component_manager.dish_dev_name
>>>>>>> 0f6bbb0 (improve loggers)
=======
                "Adapter for device :%s not found ", self.component_manager.dish_dev_name
>>>>>>> 642c346 (HM-505:Resolving minor logs)
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
            result = self.set_wait_for_dishmode(DishMode.STANDBY_FP)
            if not result:
                self.logger.error(
<<<<<<< HEAD
<<<<<<< HEAD
                    "Timeout occurred while invoking the SetStandbyFPMode "
<<<<<<< HEAD
<<<<<<< HEAD
                    "Command.",
                )
                return (
                    ResultCode.FAILED,
                    "Timeout occurred while invoking the SetStandbyFPMode "
                    "Command.",
=======
                    + "Command.",
=======
                    "Timeout occurred while invoking/processing"
=======
                    "Timeout occurred while processing"
>>>>>>> e85d945 (HM-505:Resolving review comments)
                    + " the SetStandbyFPMode "
                    + "command.",
>>>>>>> 7dcc7cc (HM-505:Resolving review comments)
                )
                return (
                    ResultCode.FAILED,
                    (
                        "Timeout occurred while invoking the SetStandbyFPMode "
                        + "command."
                    ),
>>>>>>> 9708235 (HM-505: Resolving linting issues)
=======
                    + "Command.",
                )
                return (
                    ResultCode.FAILED,
                    (
                        "Timeout occurred while invoking the SetStandbyFPMode "
                        + "Command."
                    ),
>>>>>>> 9708235 (HM-505: Resolving linting issues)
                )
        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetStandbyLPMode"
        )
        result = self.set_wait_for_dishmode(DishMode.STANDBY_LP)
        if not result:
            self.logger.error(
                "Timeout occurred while processing the"
                + " SetStandbyLPMode Command."
            )
            return (
                ResultCode.FAILED,
<<<<<<< HEAD
<<<<<<< HEAD
                "Timeout occurred while invoking the SetStandbyLPMode "
                "Command.",
=======
                (
                    "Timeout occurred while invoking the SetStandbyLPMode "
                    + "command."
                ),
>>>>>>> 9708235 (HM-505: Resolving linting issues)
=======
                (
                    "Timeout occurred while invoking the SetStandbyLPMode "
                    + "Command."
                ),
>>>>>>> 9708235 (HM-505: Resolving linting issues)
            )

        return result_code[0], message[0]
