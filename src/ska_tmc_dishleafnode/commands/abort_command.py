"""
Abort command class for DishLeafNode.
"""
from typing import Tuple

from ska_tango_base.commands import FastCommand, ResultCode

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class Abort(DishLNCommand, FastCommand):
    """
    A class for DishLeafNode's Abort() command.
    Command to abort the Dish Master and bring it to its ABORTED state.
    """

    def __init__(
        self, component_manager, op_state_model=None, logger=None
    ) -> None:
        super().__init__(
            component_manager,
            op_state_model,
            adapter_factory=None,
            logger=None,
        )
        self.component_manager = component_manager
        self.logger = logger

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
        self.logger.info("Abort command executed successfully.")
        return result_code, message
