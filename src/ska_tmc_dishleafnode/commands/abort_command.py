"""
AbortCommands command class for DishLeafNode.
"""
from __future__ import annotations

from typing import Any, Tuple

from ska_tango_base.commands import FastCommand, ResultCode
from ska_tmc_common.enum import PointingState

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class ArgumentValidator:  # pylint: disable=too-few-public-methods
    """Base class for command argument validators."""

    def validate(
        self: ArgumentValidator, *args: Any, **kwargs: Any
    ) -> tuple[tuple[Any, ...], dict[str, Any]]:
        """
        Parse and/or validate the call arguments.

        This is a default implementation that performs no parsing or
        validating, and simply returns the arguments as received.

        Subclasses may override this method to parse, validate and
        transform the arguments.

        :param args: positional args to the command
        :param kwargs: keyword args to the command

        :return: an (args, kwargs) tuple with which to invoke the do()
            hook. This default implementation simply returns the
            arguments as received.
        """
        return (args, kwargs)


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
        if result_code[0] == ResultCode.FAILED:
            return result_code[0], message[0]
        # call stop_tracking_thread to stop live thread
        result_code, message = self.stop_dish_tracking()

        self.logger.info(
            f"AbortCommands command invoked, Result code is {result_code[0]}\
                and Message is {message[0]}"
        )
        return result_code[0], message[0]

    def stop_dish_tracking(self):
        """Method to invoke track stop when abortcommands command is invoked"""
        self.component_manager.event_track_time.set()
        pointing_state = self.component_manager.pointingState
        # Check Pointing State is track before calling track stop.
        if pointing_state == PointingState.TRACK:
            return self.call_adapter_method("Dish Master", self.dish_master_adapter, "TrackStop")
        return [ResultCode.OK], [""]
