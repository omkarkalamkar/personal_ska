"""
SetKValue command class for DishLeafNode.
"""

from typing import Tuple

from ska_tango_base.commands import ArgumentValidator, FastCommand, ResultCode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand


class SetKValue(DishLNCommand, FastCommand):
    """
    A class for DishLeafNode's SetKValue() command.
    Command to set k value the Dish Master.
    k value specifies an offset in sample rate.
    The sample rate for each Band is calculated based on k value
    """

    def __init__(self, component_manager, op_state_model=None, logger=None) -> None:
        super().__init__(
            component_manager=component_manager,
            op_state_model=op_state_model,
            adapter_factory=None,
            logger=logger,
        )
        self._validator = ArgumentValidator()
        self._name = "SetKValue"

    # pylint: disable=arguments-differ
    # pylint: disable=signature-differs
    def do(self, argin: int) -> Tuple[ResultCode, str]:
        """
        Invokes SetKValue command on the DishMaster.

        CentralNode invokes SetKValue command on Dish Leaf Node
        as part of LoadDishCfg Command.
        Dish Leaf Node then invokes command on dish master
        which will then set this k value on SPFRx.

        :param argin:
            Accepts input k value that is in range [1-2222]
        :dtype: int

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
            "Dish Master", self.dish_master_adapter, "SetKValue", argin
        )
        if result_code[0] == ResultCode.OK:
            self.component_manager.kvalue = argin
        self.logger.info(
            f"SetKValue command invoked, Result code is {result_code}\
                and Message is {message}"
        )
        return result_code[0], message[0]
