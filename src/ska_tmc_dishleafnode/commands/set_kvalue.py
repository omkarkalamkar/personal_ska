"""
SetKValue command class for DishLeafNode.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ArgumentValidator, FastCommand, ResultCode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)
if TYPE_CHECKING:
    from ..manager.component_manager import DishLNComponentManager


class SetKValue(DishLNCommand, FastCommand):
    """
    A class for DishLeafNode's SetKValue() command.
    Command to set k value the Dish Master.
    k value specifies an offset in sample rate.
    The sample rate for each Band is calculated based on k value
    """

    def __init__(
        self: SetKValue,
        component_manager: DishLNComponentManager,
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
        self._name = "SetKValue"

    # pylint: disable=arguments-differ
    # pylint: disable=signature-differs
    def do(self: SetKValue, argin: int) -> Tuple[ResultCode, str]:
        """
        Invokes SetKValue command on the DishMaster.

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
            self.logger.debug(
                "Adapter for : %s is not found ",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetKValue", argin
        )
        if result_code[0] == ResultCode.OK:
            self.component_manager.kValue = argin
            self.component_manager.kValueValidationResult = ResultCode.OK

        self.logger.info(
            "Command ID: %s |"
            + " SetKValue command executed on %s "
            + "ResultCode: %s, Message: %s",
            str(self.component_manager.command_id),
            self.component_manager.dish_dev_name,
            result_code,
            message,
        )

        return result_code[0], message[0]
