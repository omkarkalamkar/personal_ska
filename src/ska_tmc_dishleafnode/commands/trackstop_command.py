"""TrackStop command class for Dishleafnode."""
from __future__ import annotations

import logging
from typing import Dict, Tuple, Union

from ska_control_model import HealthState
from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import TimeKeeper
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE

configure_logging()
LOGGER = logging.getLogger(__name__)


class TrackStop(DishLNCommand):
    """
    A class for Dishleafnode's TrackStop command. TrackStop command is
    inherited from DishLNCommand.

    This command invokes TrackStop command on Dish Master
    """

    def __init__(
        self: TrackStop,
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
        if self.component_manager.command_unique_id_dict.get(
            self.command_uniq_id
        ):
            del self.component_manager.command_unique_id_dict[
                self.command_uniq_id
            ]
            self.command_uniq_id = ""

    # pylint: disable=unused-argument
    @timeout_tracker
    @error_propagation_tracker("get_track_stop_result_code", [ResultCode.OK])
    def trackstop(
        self: TrackStop,
    ) -> Tuple[ResultCode, str]:
        """This is a long running method for TrackStop command, it
        executes the do hook, invoking TrackStop command on Dish Master

        :return: A tuple containing the result code and a message.
        :rtype: Tuple[ResultCode, str]
        """
        return self.do()

    # pylint: disable=arguments-differ
    def do(self: TrackStop) -> Tuple[ResultCode, str]:
        """
        Method to invoke TrackStop command on Dish Master.
        return:
            (ResultCode, str)
        """

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.debug(
                "Command ID: %s | Adapter for : %s is not found",
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
            result_code, msg = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "TrackStop"
            )
            if ResultCode(result_code[0]) is ResultCode.QUEUED:
                # Append command unique id
                self.component_manager.command_unique_id_dict[
                    "TrackStop"
                ] = msg[0]
                self.command_uniq_id = msg[0]
            self.logger.info(
                "Command ID: %s |"
                + "TrackStop command executed on %s ,"
                + "with ResultCode: %s, Message: %s",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
                ResultCode(result_code[0]),
                msg,
            )
            if result_code[0] in [
                ResultCode.FAILED,
                ResultCode.REJECTED,
                ResultCode.NOT_ALLOWED,
            ]:
                message = (
                    f"TrackStop result code: {result_code[0]} "
                    + f"and message: {msg[0]}"
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
            if self.component_manager._update_health_state_callback:
                self.component_manager._update_health_state_callback(
                    HealthState.DEGRADED
                )
            result_code = [ResultCode.FAILED]
            message += (
                " StopProgramTrackTable: "
                " There was an error while stopping the generation of "
                + f"program track table: {exception}"
            )
        if not message:
            message = COMMAND_COMPLETION_MESSAGE
        return result_code[0], message
