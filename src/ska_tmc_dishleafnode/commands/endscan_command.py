"""EndScan command class for Dishleafnode."""
from __future__ import annotations

import logging
from typing import Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tmc_common import (
    TimeKeeper,
    error_propagation_decorator,
    timeout_decorator,
)

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class EndScan(DishLNCommand):
    """
    A class for Dishleafnode's EndScan command. EndScan command is
    inherited from DishLNCommand.

    This command sets scanID attribute of Dish Master to empty string.
    """

    def __init__(
        self: EndScan,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, logger
        )

    # pylint: disable=unused-argument
    @timeout_decorator
    @error_propagation_decorator("get_end_scan_result_code", [ResultCode.OK])
    def endscan(
        self: EndScan,
    ) -> Tuple[ResultCode, str]:
        """This is a method for long running command EndScan command, it
        executes the do hook, to set scanID attribute of Dish Master to empty
        string.

        :return: A tuple containing the result code and a message.
        :rtype: Tuple[ResultCode, str]
        """
        return self.do()

    # pylint: disable=arguments-differ
    def do(self: DishLNCommand):
        """
        Method to set scanID attribute of Dish Master to empty string.

        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Error while creating adapter %s",
                self.component_manager.dish_dev_name,
            )
            return result_code, message
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "EndScan"
            )
        return result_code[0], message[0]
