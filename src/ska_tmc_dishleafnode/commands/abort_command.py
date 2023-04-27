"""
Abort command class for DishLeafNode.
"""
from typing import Tuple

from ska_tango_base.commands import FastCommand, ResultCode
from ska_tmc_common.enum import DishMode, PointingState

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class Abort(DishLNCommand, FastCommand):
    """
    A class for DishLeafNode's Abort() command.
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

        ret_code, message = self.init_adapter()

        if ret_code == ResultCode.FAILED:
            return ret_code, message

        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "Abort"
        )
        # call stop_dish_tracking to invoke track stop command
        self.stop_dish_tracking()

        self.logger.info("Abort command invoked successfully.")
        return result_code, message

    def stop_dish_tracking(self):
        """Method to invoke track stop when abort command is invoked"""
        self.component_manager.event_track_time.set()
        current_dish_mode = self.component_manager.dishMode
        pointing_state = self.component_manager.pointingState
        # Check whether DishMode is Operate and Pointing State is track before calling track stop.
        if current_dish_mode == DishMode.OPERATE and pointing_state == PointingState.TRACK:
            ret_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "TrackStop"
            )
            if ret_code == ResultCode.FAILED:
                self.logger.error(f"TrackStop Invocation Failed {message}")
            else:
                self.logger.info("TrackStop command invoked successfully.")
            return ret_code, message
        if current_dish_mode != DishMode.OPERATE:
            message = f"TrackStop invocation failed with incorrect DishMode: {current_dish_mode}"
        if pointing_state != PointingState.TRACK:
            message = f"TrackStop invocation failed with incorrect PointingState: {pointing_state}"
        return ResultCode.FAILED, message
