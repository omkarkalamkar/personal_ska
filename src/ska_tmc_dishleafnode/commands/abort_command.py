"""
AbortCommands command class for DishLeafNode.
"""

from typing import Tuple

from ska_tango_base.commands import ArgumentValidator, FastCommand, ResultCode
from ska_tmc_common.enum import PointingState

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand


class AbortCommands(DishLNCommand, FastCommand):
    """
    A class for DishLeafNode's AbortCommands() command.
    Command to abort the Dish Master and bring it to its ABORTED state.
    """

    def __init__(self, component_manager, op_state_model=None, logger=None) -> None:
        super().__init__(
            component_manager=component_manager,
            op_state_model=op_state_model,
            adapter_factory=None,
            logger=logger,
        )
        self._validator = ArgumentValidator()
        self._name = "AbortCommands"

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
            self.logger.info("%s adapter not found ", self.component_manager.dish_dev_name)
            return result_code, message

        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "AbortCommands"
        )
        if result_code[0] == ResultCode.FAILED:
            return result_code[0], message[0]
        # call stop_tracking_thread to stop live thread
        result_code, message = self.stop_dish_tracking()

        self.logger.info(
            f"AbortCommands command invoked, Result code is {result_code}\
                and Message is {message}"
        )
        return result_code, message

    def stop_dish_tracking(self):
        """Method to invoke track stop when abortcommands command is invoked"""
        self.component_manager.event_track_time.set()
        pointing_state = self.component_manager.pointingState
        # Check Pointing State is track before calling track stop.
        if pointing_state == PointingState.TRACK:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "TrackStop"
            )
            return result_code[0], message[0]
        return ResultCode.OK, ""
