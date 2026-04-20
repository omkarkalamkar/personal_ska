"""TrackStop command class for Dishleafnode."""
from __future__ import annotations

import logging
from typing import Callable, Dict, Optional, Tuple, Union

from ska_control_model import TaskStatus
from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class TrackStop(DishLNCommand):
    """
    A class for Dishleafnode's TrackStop command. TrackStop command is
    inherited from DishLNCommand.

    This command invokes TrackStop command on Dish Master
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
            del self.component_manager.command_unique_id_dict["TrackStop"]
            self.command_uniq_id = ""
        self.component_manager.receiver_band = ""
        self.component_manager.update_rxband_health_aggregation()
        self.component_manager.update_healthinfo_errors()

    # pylint: disable=unused-argument
    # @timeout_tracker
    # @error_propagation_tracker("get_track_stop_result_code", [ResultCode.OK])
    def trackstop(
        self: TrackStop,
        task_callback: Callable = None,
        task_abort_event: Optional[object] = None,
        **kwargs,
    ) -> Tuple[ResultCode, str]:
        """This is a long running method for TrackStop command, it
        executes the do hook, invoking TrackStop command on Dish Master

        :return: A tuple containing the result code and a message.
        :rtype: Tuple[ResultCode, str]
        """
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        self.component_manager.abort_event = task_abort_event
        result_code, message = self.do()
        self.call_update_task_status(result_code, message)
        return result_code, message

    # pylint: disable=arguments-differ
    def do(self: TrackStop) -> Tuple[ResultCode, str]:
        """
        Method to invoke TrackStop command on Dish Master.

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
        # Stop the thread which started when Track command was invoked
        result_code, message = [ResultCode.OK], ""
        with self.component_manager.tango_operation_execution_lock:
            self.logger.debug(
                "Command ID: %s | Acquired tango lock",
                self.component_manager.command_id,
            )
            result_code, message = self.invoke_command_and_track(
                self.dish_master_adapter, "TrackStop"
            )
            if ResultCode(result_code) is ResultCode.QUEUED:
                # Append command unique id
                self.component_manager.command_unique_id_dict[
                    "TrackStop"
                ] = message
                self.command_uniq_id = message
            self.logger.info(
                "Command ID: %s | "
                + "TrackStop command invoked on %s, "
                + "with ResultCode: %s, Message: %s",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
                ResultCode(result_code),
                message,
            )
            if result_code in [
                ResultCode.FAILED,
                ResultCode.REJECTED,
                ResultCode.NOT_ALLOWED,
            ]:
                message = (
                    f"TrackStop result code: {result_code} "
                    + f"and message: {message}"
                )
            self.logger.debug(
                "Command ID: %s | Released tango lock",
                self.component_manager.command_id,
            )

        try:
            self.dishln_pointing_device_adapter.StopProgramTrackTable()
        except Exception as exception:
            self.logger.exception(
                "Command ID: %s | Unable to stop programTrackTable: %s",
                self.component_manager.command_id,
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
            result_code = ResultCode.FAILED
            message += (
                " StopProgramTrackTable: "
                " There was an error while stopping the generation of "
                + f"program track table: {exception}"
            )
        if result_code != ResultCode.OK:
            return result_code, message
        return self.wait_for_completion()
