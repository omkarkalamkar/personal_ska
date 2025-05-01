"""
Abort command class for DishLeafNode.
"""
from __future__ import annotations

import logging
import threading
from typing import Dict, Optional, Tuple, Union

from ska_control_model import HealthState
from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import TimeKeeper
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.dish_ln_command import (
    DishLNCommand,
    task_callback_default,
)
from ska_tmc_dishleafnode.constants import COMMAND_STARTED_MESSAGE

configure_logging()
LOGGER = logging.getLogger(__name__)


class Abort(DishLNCommand):
    """
    A class for DishLeafNode's Abort() command.
    Command to abort the Dish Master and bring it to its ABORTED state.
    """

    def __init__(
        self: Abort,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, logger
        )
        self.command_uniq_id: str = ""

    # pylint: disable=unused-argument
    @timeout_tracker
    @error_propagation_tracker("get_abort_result_code", [ResultCode.OK])
    def invoke_abort(
        self,
        task_callback: TaskCallbackType = task_callback_default,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """This method calls do for Abort command"""
        self.component_manager.command_in_progress = "Abort"
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.do()
            return result_code, message

    # pylint: enable=unused-argument

    def update_task_status(
        self,
        **kwargs: Dict[str, Union[Tuple[ResultCode, str], TaskStatus, str]],
    ) -> None:
        """
        Update the status of a task.

        Args:
            **kwargs: Keyword arguments for task status update.
        """
        result = kwargs.get("result")
        status = kwargs.get("status", TaskStatus.COMPLETED)
        message = kwargs.get("exception")

        self.logger.info(
            "Command ID: %s | Updating task status with Result: %s",
            self.command_uniq_id,
            kwargs,
        )

        if result:
            if result[0] == ResultCode.OK and status == TaskStatus.COMPLETED:
                self.task_callback(status=status, result=result)
            else:
                self.task_callback(
                    status=status, result=result, exception=message
                )
        self.component_manager.command_in_progress = ""
        if self.component_manager.command_unique_id_dict.get(
            self.command_uniq_id
        ):
            del self.component_manager.command_unique_id_dict[
                self.command_uniq_id
            ]
            self.command_uniq_id = ""
        self.component_manager.clear_configure_command_events_flags()

    # pylint: disable=arguments-differ

    def do(self) -> Tuple[ResultCode, str]:
        """
        Invokes Abort command on the DishMaster.

        param argin:
            None

        return:
            A tuple containing a return code and a
            string message indicating status.
            The message is for information purpose only.

        rtype:
            (ResultCode, str)

        """
        self.logger.debug(
            "Command ID: %s | Command in progress: %s" + " on : %s",
            self.command_uniq_id,
            self.component_manager.command_in_progress,
            self.component_manager.dish_dev_name,
        )
        self.component_manager.abort_event.set()
        self.logger.debug(
            "Command ID: %s | Abort event set for : %s",
            self.command_uniq_id,
            self.component_manager.dish_dev_name,
        )
        with self.component_manager.command_result_update_lock:
            self.component_manager.observable.notify_observers(
                attribute_value_change=True
            )
        self.component_manager.abort_event.clear()
        if not self.component_manager.command_in_progress:
            self.component_manager.abort_event.clear()
            self.logger.debug(
                "Command ID: %s | Cleared abort event for: %s",
                self.command_uniq_id,
                self.component_manager.dish_dev_name,
            )

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter for device : %s is not found.",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        self.logger.info(
            "Dish Abort commands device property is: %s",
            self.component_manager.is_dish_abort_commands_enabled,
        )

        if self.component_manager.is_dish_abort_commands_enabled:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Abort"
            )
            # Append command unique id
            self.component_manager.command_unique_id_dict["Abort"] = message[0]
            self.logger.info(
                "Command ID: %s | "
                + "Abort() command has been invoked, the result code"
                + " is %s and the message is %s",
                self.command_uniq_id,
                result_code[0],
                message[0],
            )
            if result_code[0] in [
                ResultCode.REJECTED,
                ResultCode.NOT_ALLOWED,
                ResultCode.ABORTED,
            ]:
                return result_code[0], message[0]

        # call stop_tracking_thread to stop live thread
        result_code, message = self.stop_program_track_table()
        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            return result_code, message

        self.component_manager.clear_track_table_errors()

        self.logger.debug(
            "Abort command executed successfully on the DishLeafNode."
        )
        return ResultCode.STARTED, COMMAND_STARTED_MESSAGE

    def stop_program_track_table(self) -> Tuple[ResultCode, str]:
        """Method to invoke StopProgramTrackTable() when abort command is
            invoked.

        rtype:
            (ResultCode, str)
        """
        result_code, message = [ResultCode.OK], ""

        try:
            self.dishln_pointing_device_adapter.StopProgramTrackTable()
        except Exception as exception:
            self.logger.exception(
                "Unable to stop programTrackTable: %s",
                exception,
            )
            self.component_manager.current_track_table_error = (
                f"Exception while stopping programTrackTable {exception}"
            )
            if self.component_manager._update_health_state_callback:
                self.component_manager._update_health_state_callback(
                    HealthState.DEGRADED
                )
                result_code = [ResultCode.FAILED]
                message += (
                    " StopProgramTrackTable: There was an error while"
                    + " stopping the generation of "
                    + f"program track table: {exception}"
                )

        return result_code[0], message
