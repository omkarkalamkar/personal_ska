"""
SetStowMode command class for DishLeafNode.
"""
from __future__ import annotations

from typing import Tuple

from ska_tango_base.commands import ResultCode
from ska_tmc_common import DishMode
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand


class SetStowMode(DishLNCommand):
    """
    A class for DishleafNode's SetStowMode() command.

    SetStowMode command on DishLeafNode enables the telescope to perform
    further operations and observations. It Invokes SetStowMode command on
    Dish Leaf Node device.
    """

    @timeout_tracker
    @error_propagation_tracker(
        "get_dish_mode",
        [DishMode.STOW],
    )
    def set_stow_mode(self: SetStowMode):
        """A method to invoke the SetStowMode command.
        It sets the task_callback status according to command progress.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        return self.do()

    # pylint: disable=arguments-differ
    def do(self: SetStowMode) -> Tuple[ResultCode, str]:
        """
        Method to invoke SetStowMode command on DishMaster.

        Returns:
            Tuple[ResultCode, str]: Tuple of ResultCode and message.

        """

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.debug(
                "Command ID: %s | Adapter for : %s is not found ",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
            )
            return result_code, message
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "SetStowMode"
            )

        return result_code[0], message[0]
