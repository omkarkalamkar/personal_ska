"""
Abort command class for DishLeafNode.
"""
from __future__ import annotations

import logging
import threading
from typing import Dict, Optional, Tuple, Union

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
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

    # pylint: disable=unused-argument
    @timeout_tracker
    @error_propagation_tracker(
        "is_abort_completed",
        [True],
    )
    def invoke_abort(
        self,
        task_callback: TaskCallbackType = task_callback_default,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """This method calls do for Abort command"""
        with self.component_manager.tango_operation_execution_lock:
            return self.do()

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

        self.logger.debug(
            "Command ID: %s | Updating Task status with Result: %s",
            self.component_manager.command_id,
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
        if (
            self.command_uniq_id
            in self.component_manager.command_unique_id_dict.values()
        ):
            del self.component_manager.command_unique_id_dict["Abort"]
            self.command_uniq_id = ""
        self.component_manager.clear_configure_command_events_flags()
        self.component_manager.receiver_band = ""
        self.component_manager.update_rxband_health_aggregation()
        self.component_manager.update_healthinfo_errors()

    # pylint: disable=arguments-differ

    def do(self) -> Tuple[ResultCode, str]:
        """
        Invokes Abort command on the DishMaster.

        Returns:
            Tuple[ResultCode, str]:
            A tuple containing a return code and a
            string message indicating status.
            The message is for information purpose only.

        """
        self.logger.debug(
            "Command ID: %s | Command in progress: %s ",
            self.component_manager.command_id,
            self.component_manager.command_in_progress,
        )
        self.component_manager.abort_event.set()
        self.logger.info(
            "Command ID: %s | Abort event set",
            self.component_manager.command_id,
        )
        with self.component_manager.command_result_update_lock:
            self.component_manager.observable.notify_observers(
                attribute_value_change=True
            )
        self.component_manager.abort_event.clear()
        if not self.component_manager.command_in_progress:
            self.component_manager.abort_event.clear()
            self.logger.debug(
                "Command ID: %s | Cleared abort event ",
                self.component_manager.command_id,
            )

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter for device : %s is not found.",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        self.logger.debug(
            "Dish Abort commands device property is: %s",
            self.component_manager.is_dish_abort_commands_enabled,
        )

        if self.component_manager.is_dish_abort_commands_enabled:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Abort"
            )
            # Append command unique id
            self.component_manager.command_unique_id_dict["Abort"] = message[0]
            self.command_uniq_id = message[0]
            self.logger.info(
                "Command ID: %s | "
                + "Abort() command has been invoked with ResultCode:"
                + " %s, Message: %s",
                self.component_manager.command_id,
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

        self.logger.info(
            "Abort command executed successfully on the DishLeafNode."
        )
        return ResultCode.STARTED, COMMAND_STARTED_MESSAGE

    def stop_program_track_table(self) -> Tuple[ResultCode, str]:
        """Method to invoke StopProgramTrackTable() when abort command is
        invoked.

        Returns:
            Tuple[ResultCode, str]: Tuple of ResultCode and message.
        """
        result_code, message = [ResultCode.OK], ""

        try:
            self.dishln_pointing_device_adapter.StopProgramTrackTable()
        except Exception as exception:
            self.logger.exception(
                "Unable to stop programTrackTable: %s",
                str(exception),
            )
            self.component_manager.current_track_table_error = (
                f"Exception while stopping programTrackTable {exception}"
            )

            health_manager = self.component_manager.health_manager
            update_health_data_and_aggregate = (
                health_manager.update_health_data_and_aggregate
            )

            update_health_data_and_aggregate(
                {"Track_Table_Stop_Error": exception},
                "ProgramtracktableErrors",
            )
            result_code = [ResultCode.FAILED]
            message += (
                " StopProgramTrackTable: There was an error while"
                + " stopping the generation of "
                + f"program track table: {exception}"
            )

        return result_code[0], message
