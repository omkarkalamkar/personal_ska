"""Scan command class for Dishleafnode."""
from __future__ import annotations

import logging
from typing import Callable, Dict, Optional, Tuple, Union

from ska_control_model import TaskStatus
from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class Scan(DishLNCommand):
    """
    A class for Dishleafnode's Scan command. Scan command is
    inherited from DishLNCommand.

    This command invokes Scan command on Dish Master
    """

    def __init__(
        self: Scan,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        # self.timekeeper = TimeKeeper(
        #     self.component_manager.command_timeout, logger
        # )
        self.command_uniq_id: str = ""

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
        # Previously configure command used to clear this dictionary
        # But it was happening once Scan has started , causing entries
        # of Scan command get erased , to avoid this dictionary will now
        # be cleared from here.
        self.component_manager.command_unique_id_dict.clear()
        self.command_uniq_id = ""
        # if self.component_manager.command_unique_id_dict.get(
        #     self.command_uniq_id
        # ):
        #     del self.component_manager.command_unique_id_dict[
        #         self.command_uniq_id
        #     ]
        #     self.command_uniq_id = ""

    # pylint: disable=unused-argument
    # @timeout_tracker
    # @error_propagation_tracker("get_scan_result_code", [ResultCode.OK])
    def scan(
        self: Scan,
        argin: str,
        task_callback: Callable = None,
        task_abort_event: Optional[object] = None,
        **kwargs,
    ) -> Tuple[ResultCode, str]:
        """This is a long running method for Scan command, it
        executes the do hook, invoking Scan command on Dish Master

        :param argin: Input JSON string
        :type argin: str

        :return: A tuple containing the result code and a message.
        :rtype: Tuple[ResultCode, str]
        """
        self.task_callback = task_callback
        self.component_manager.abort_event = task_abort_event
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        result_code, message = self.do(argin)
        self.call_update_task_status(result_code, message)
        return result_code, message

    # pylint: disable=signature-differs
    def do(self: Scan, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke Scan command on Dish Master.

        Args:
            argin (str): json string for Scan command.

        Returns:
            Tuple[ResultCode, str]: Tuple of ResultCode and message.
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Command ID: %s | Adapter not found for %s",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.invoke_command_and_track(
                self.dish_master_adapter, "Scan", argin
            )
            if ResultCode(result_code) is ResultCode.QUEUED:
                # Append command unique id
                self.component_manager.command_unique_id_dict[
                    "Scan"
                ] = message[0]
                self.command_uniq_id = message[0]
            self.logger.info(
                "Command ID: %s |"
                + " Scan command invoked on %s "
                + "ResultCode: %s, Message: %s",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
                ResultCode(result_code),
                message,
            )
        if result_code == ResultCode.FAILED:
            return result_code, message

        return self.wait_for_completion()
