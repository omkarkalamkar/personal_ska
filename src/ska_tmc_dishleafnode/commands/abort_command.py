"""
Abort command class for DishLeafNode.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, Optional, Tuple, Union

from ska_control_model import TaskStatus
from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class Abort(DishLNCommand):
    """
    A class for DishLeafNode's Abort() command.
    Command to abort the Dish Master and bring it to its ABORTED state.
    """

    # pylint: disable=unused-argument
    def invoke_abort(
        self,
        task_callback: Callable = None,
        task_abort_event: Optional[object] = None,
        **kwargs,
    ):
        """Invoke Abort on Dish Master and track its completion.
        Args:
            task_callback: A callback function to update the status
            of the task.
            task_abort_event: An event to signal task abortion.
        """
        self.task_callback = task_callback
        self.component_manager.abort_event = task_abort_event
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        self.set_command_id(__class__.__name__)
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.do()
            self.call_update_task_status(result_code, message)
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
        self.component_manager.set_abort_flag_for_commands()
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
                "Adapter not found for %s.",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        if self.component_manager.is_dish_abort_commands_enabled:
            result_code, message = self.invoke_command_and_track(
                self.dish_master_adapter, "Abort"
            )
            # Append command unique id
            self.logger.info(
                "Command ID: %s | "
                + "Abort() command has been invoked with ResultCode:"
                + " %s, Message: %s",
                self.component_manager.command_id,
                result_code,
                message,
            )
            if result_code in [
                ResultCode.REJECTED,
                ResultCode.NOT_ALLOWED,
                ResultCode.ABORTED,
            ]:
                return result_code, message

        # call stop_tracking_thread to stop live thread
        result_code, message = self.stop_program_track_table()

        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            return result_code, message

        self.component_manager.clear_track_table_errors()

        self.logger.info(
            "Abort command invoked successfully on the DishLeafNode."
        )
        return self.wait_for_completion(
            state_getter=self.component_manager.is_abort_completed,
            desired_state=True,
        )

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
