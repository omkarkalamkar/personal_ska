"""EndScan command class for Dishleafnode."""
from __future__ import annotations

import logging
from typing import Callable, Dict, Optional, Tuple, Union

from ska_control_model import TaskStatus
from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class EndScan(DishLNCommand):
    """
    A class for Dishleafnode's EndScan command. EndScan command is
    inherited from DishLNCommand.

    This command sets scanID attribute of Dish Master to empty string.
    """

    def update_task_status(
        self,
        **kwargs: Dict[str, Union[Tuple[ResultCode, str], TaskStatus, str]],
    ) -> None:
        """
        Update the status of a task.

        Args:
            **kwargs: Keyword arguments for task status update.
        """
        super().update_task_status(**kwargs)
        if (
            self.command_uniq_id
            in self.component_manager.command_unique_id_dict.values()
        ):
            del self.component_manager.command_unique_id_dict["EndScan"]
            self.command_uniq_id = ""

    # pylint: disable=unused-argument
    def endscan(
        self: EndScan,
        task_callback: Callable = None,
        task_abort_event: Optional[object] = None,
        **kwargs,
    ) -> Tuple[ResultCode, str]:
        """This is a method for long running command EndScan command, it
        executes the do hook, to set scanID attribute of Dish Master to empty
        string.

        :return: A tuple containing the result code and a message.
        :rtype: Tuple[ResultCode, str]
        """
        self.task_callback = task_callback
        self.component_manager.abort_event = task_abort_event
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        result_code, message = self.do()
        self.call_update_task_status(result_code, message)
        return result_code, message

    # pylint: disable=arguments-differ
    def do(self: DishLNCommand):
        """
        Method to set scanID attribute of Dish Master to empty string.

        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.debug(
                "Command ID: %s | Adapter not found for %s",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
            )
            return result_code, message
        with self.component_manager.tango_operation_execution_lock:
            # result_code, message = self.call_adapter_method(
            #     "Dish Master", self.dish_master_adapter, "EndScan"
            # )
            result_code, message = self.invoke_command_and_track(
                self.dish_master_adapter, "EndScan"
            )
            if ResultCode(result_code) is ResultCode.QUEUED:
                # Append command unique id
                self.component_manager.command_unique_id_dict[
                    "EndScan"
                ] = message[0]
                self.command_uniq_id = message[0]
            self.logger.info(
                "Command ID: %s |"
                + " EndScan command invoked on %s "
                + "ResultCode: %s, Message: %s",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
                ResultCode(result_code),
                message,
            )
        if result_code == ResultCode.FAILED:
            return result_code, message

        return self.wait_for_completion()
