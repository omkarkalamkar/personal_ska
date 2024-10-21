"""TrackStop command class for Dishleafnode."""
from __future__ import annotations

import logging
from typing import Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tmc_common import (
    TimeKeeper,
    error_propagation_decorator,
    timeout_decorator,
)

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

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
    @timeout_decorator
    @error_propagation_decorator("get_track_stop_result_code", [ResultCode.OK])
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

        self.component_manager.stop_track_table_process()
        with self.component_manager.tango_operation_execution_lock:
            self.logger.debug("Grabbed tango lock")
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "TrackStop"
            )

        self.logger.debug("Released tango lock")

        self.component_manager.stop_track_table_process()

        return result_code[0], message[0]
