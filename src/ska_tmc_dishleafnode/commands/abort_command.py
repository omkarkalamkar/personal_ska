"""
AbortCommands command class for DishLeafNode.
"""

import logging
from typing import Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ArgumentValidator, ResultCode
from ska_tmc_common.enum import PointingState

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE

configure_logging()
LOGGER = logging.getLogger(__name__)


class AbortCommands(DishLNCommand):
    """
    A class for DishLeafNode's AbortCommands() command.
    Command to abort the Dish Master and bring it to its ABORTED state.
    """

    def __init__(
        self,
        component_manager,
        op_state_model=None,
        logger: logging.Logger = LOGGER,
    ) -> None:
        super().__init__(
            component_manager=component_manager,
            op_state_model=op_state_model,
            adapter_factory=None,
            logger=logger,
        )
        self._validator = ArgumentValidator()
        self._name = "AbortCommands"

    def invoke_abort(self):
        """This method calls do for Abort command"""
        result_code, message = self.do()
        return result_code, message

    # pylint: disable=arguments-differ
    def do(self) -> Tuple[ResultCode, str]:
        """
        Invokes AbortCommands command on the DishMaster.

        param argin:
            None

        return:
            A tuple containing a return code and a
            string message indicating status.
            The message is for information purpose only.

        rtype:
            (ResultCode, str)

        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter for device : %s is not found.",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        self.logger.info(
            "Dish Abort commands device property is: %s",
            self.component_manager.is_dish_abort_commands,
        )
        if self.component_manager.is_dish_abort_commands:
            with self.component_manager.tango_operation_execution_lock:
                result_code, message = self.call_adapter_method(
                    "Dish Master", self.dish_master_adapter, "AbortCommands"
                )
            self.logger.info(
                f"AbortCommands command invoked, Result code is {result_code}\
                and Message is {message}"
            )
            if result_code[0] == ResultCode.FAILED:
                return result_code[0], message[0]

        # call stop_tracking_thread to stop live thread
        result_code, message = self.stop_dish_tracking()
        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            return result_code, message
        return ResultCode.OK, COMMAND_COMPLETION_MESSAGE

    def stop_dish_tracking(self) -> Tuple[ResultCode, str]:
        """Method to invoke track stop when abortcommands command is invoked

        rtype:
            (ResultCode, str)
        """
        self.component_manager.set_track_process_event()
        pointing_state = self.component_manager.pointingState
        # Check Pointing State is track before calling track stop.
        if pointing_state in [PointingState.TRACK, PointingState.SLEW]:
            with self.component_manager.tango_operation_execution_lock:
                result_code, message = self.call_adapter_method(
                    "Dish Master", self.dish_master_adapter, "TrackStop"
                )
            return result_code[0], message[0]
        return ResultCode.OK, ""
