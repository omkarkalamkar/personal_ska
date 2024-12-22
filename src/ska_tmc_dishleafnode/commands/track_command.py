"""Track command class for Dishleafnode."""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import TimeKeeper, TimeoutCallback, TimeoutState
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class Track(DishLNCommand):
    """
    A class for Dishleafnode's Track command. Track command is
    inherited from DishLNCommand.

    This command invokes Track command on Dish Master
    """

    def __init__(
        self: Track,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
        is_configure_command: bool = False,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.task_callback = None
        self.ra_value = ""
        self.dec_value = ""
        self.tracking_thread = None
        self.is_configure_command = is_configure_command
        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback: Callable[
            [str, TimeoutState], Optional[ValueError]
        ] = TimeoutCallback(self.timeout_id, self.logger)
        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, logger
        )
        if self.component_manager.is_configure_command:
            self.component_manager.configure_command_timer_list.append(
                self.timekeeper
            )

    # pylint: disable=unused-argument
    @timeout_tracker
    @error_propagation_tracker("get_track_result_code", [ResultCode.OK])
    def track(self: Track, argin: dict, **kwargs) -> Tuple[ResultCode, str]:
        """This is a long running method for Track command, it
        executes the do hook, invoking Track command on Dish Master

        :param argin: Input JSON string
        :type argin: dict
        :return: : (ResultCode, str)
        :rtype: Tuple
        """
        # Indicate that the task has started
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        if self.is_configure_command is False:
            self.set_command_id(__class__.__name__)
        else:
            self.component_manager.command_in_progress = "Configure"

        return self.do(argin)

    def validate_json_argument(self: Track, input_argin: dict) -> tuple:
        """Validates the json argument"""
        target = input_argin.get("pointing", {}).get("target", {})
        ra_value = target.get("ra")
        dec_value = target.get("dec")
        if not ra_value or not dec_value:
            return (
                ResultCode.FAILED,
                "ra or dec value key is not present in the input json.",
            )

        return (ResultCode.OK, "")

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self: Track, argin: dict) -> Tuple[ResultCode, str]:
        """
        Method to invoke Track command on Dish Master.

        param argin: dict

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

        with self.component_manager.tango_operation_execution_lock:
            self.logger.debug("Acquired  tango lock")
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Track"
            )

        self.logger.debug("Released tango lock")

        if result_code[0] == ResultCode.FAILED:
            return result_code[0], message[0]

        return result_code[0], message[0]
