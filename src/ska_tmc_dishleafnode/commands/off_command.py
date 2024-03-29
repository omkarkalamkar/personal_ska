"""On command class for Dishleafnode."""

import threading
from logging import Logger
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.enum import DishMode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand


class Off(DishLNCommand):
    """
    A class for Dishleafnode's Off command. Off command is
    inherited from DishLNCommand.

    This command invokes off command on Dish Master
    """

    # pylint: disable=unused-argument
    def invoke_off(
        self,
        logger: Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        A method to invoke the Off command.
        It sets the task_callback status according to command progress.

        :param argin: Input JSON string
        :type argin : str
        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)
        return_code, message = self.do()
        logger.info(message)
        if return_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(return_code),
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(return_code),
            )

    def do(self, argin=None):
        """
        "Invokes StandbyFP and StandbyLP mode commands on dish master device
        after waiting for correct dish modes. First invokes and waits for
        completion of SetStandbyFPMode command, then invokes and waits for
        completion of SetStandbyLPMode command."

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
                    "Timeout occurred while invoking the SetStandbyFPMode "
                    + "Command.",
                )
                return (
                    ResultCode.FAILED,
                    "Timeout occurred while invoking the SetStandbyFPMode "
                    + "Command.",
                )
        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetStandbyLPMode"
        )
        result = self.set_wait_for_dishmode(DishMode.STANDBY_LP)
        if not result:
            self.logger.error(
                "Timeout occurred while invoking the SetStandbyLPMode Command."
            )
            return (
                ResultCode.FAILED,
                "Timeout occurred while invoking the SetStandbyLPMode "
                + "Command.",
            )

        return result_code[0], message[0]
