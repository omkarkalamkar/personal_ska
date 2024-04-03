"""
SetStandbyLPMode command class for DishLeafNode.
"""
import threading
from logging import Logger
from typing import Optional, Tuple

from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand


class SetStandbyLPMode(DishLNCommand):
    """
    A class for DishLeafNode's SetStandbyLPMode() command.

    Invokes SetStandbyLPMode (i.e. Low Power State) command on DishMaster.

    """

    # pylint: disable=unused-argument
    def set_standby_lp_mode(
        self,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """A method to invoke the SetStandbyLPMode command.
        It sets the task_callback status according to command progress.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional

        :rtype: None
        """

        task_callback(status=TaskStatus.IN_PROGRESS)

        result_code, message = self.do()
        logger.info(message)
        if result_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(result_code),
                exception=message,
            )
        else:
            logger.info(
                "The SetStandbyLPMode command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(result_code),
            )

    # pylint: disable=arguments-differ
    def do(self) -> Tuple[ResultCode, str]:
        """
        Method to invoke SetStandbyLPMode (Low power mode) command on
        DishMaster.

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

        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetStandbyLPMode"
        )

        return result_code[0], message[0]
