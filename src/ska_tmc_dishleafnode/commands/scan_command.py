"""Scan command class for Dishleafnode."""
from __future__ import annotations

import logging
from typing import Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tmc_common import TimeKeeper
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class Scan(DishLNCommand):
    """
    A class for Dishleafnode's Scan command. Scan command is
    inherited from DishLNCommand.

    This command invokes Scan command on Dish Master
    """

    def __init__(
        self: Scan,
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
    @timeout_tracker
    @error_propagation_tracker("get_scan_result_code", [ResultCode.OK])
    def scan(
        self: Scan,
        argin: str,
    ) -> Tuple[ResultCode, str]:
        """This is a long running method for Scan command, it
        executes the do hook, invoking Scan command on Dish Master

        :param argin: Input JSON string
        :type argin: str

        :return: A tuple containing the result code and a message.
        :rtype: Tuple[ResultCode, str]
        """
        return self.do(argin)

    # pylint: disable=signature-differs
    def do(self: Scan, argin: str):
        """
        Method to invoke Scan command on Dish Master.

        param argin:
            str

        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter for device : %s is not found ",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Scan", argin
            )

        self.logger.info(
            "Scan command -> Result Code: %s, msg: %s", result_code, message
        )
        # Append command unique id
        self.component_manager.command_unique_id_list.append(message[0])
        return result_code[0], message[0]
