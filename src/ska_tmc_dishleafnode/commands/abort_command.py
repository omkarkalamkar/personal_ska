"""
Abort command class for DishLeafNode.
"""
from typing import Tuple

from ska_tango_base.commands import FastCommand, ResultCode

from ska_tmc_common.enum import PointingState
from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


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
            return result_code, message

        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "AbortCommands"
        )
        if result_code == ResultCode.FAILED:
            return result_code, message
        # call stop_tracking_thread to stop live thread
        result_code, message = self.stop_dish_tracking()

        self.logger.info("AbortCommands command invoked successfully.")
        return result_code, message

    def stop_dish_tracking(self):
        """Method to invoke track stop when abortcommands command is invoked"""
        self.component_manager.event_track_time.set()
        pointing_state = self.component_manager.pointingState
        # Check Pointing State is track before calling track stop.
        if pointing_state == PointingState.TRACK:
            return self.call_adapter_method("Dish Master", self.dish_master_adapter, "TrackStop")
        return ResultCode.OK, ""
