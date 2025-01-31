"""TrackStop command class for Dishleafnode."""
from __future__ import annotations

import logging
from typing import Tuple

from ska_control_model import HealthState
from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
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
            self.logger.error(
                "Adapter for device : %s is not found",
                self.component_manager.dish_dev_name,
            )
            return result_code, message
        # Stop the thread which started when Track command was invoked
        result_code, message = [ResultCode.OK], ""
        with self.component_manager.tango_operation_execution_lock:
            self.logger.debug("Acquired  tango lock")
            result_code, msg = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "TrackStop"
            )
            self.logger.debug(
                "TrackStop command returned ResultCode: %s, message: %s",
                result_code,
                msg,
            )
            if result_code[0] is not ResultCode.FAILED:
                # Append command unique id
                self.component_manager.command_unique_id_list.append(msg[0])
            if result_code[0] in [
                ResultCode.FAILED,
                ResultCode.REJECTED,
                ResultCode.NOT_ALLOWED,
            ]:
                message = (
                    f"TrackStop result code: {result_code[0]} "
                    + f"and message: {msg[0]}"
                )
            self.logger.debug("Released tango lock")

        try:
            self.logger.info("Invoking stop program track table cmd")
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
                " StopProgramTrackTable: "
                " There was an error while stopping the generation of "
                + f"program track table: {exception}"
            )
        if not message:
            message = COMMAND_COMPLETION_MESSAGE
        return result_code[0], message
