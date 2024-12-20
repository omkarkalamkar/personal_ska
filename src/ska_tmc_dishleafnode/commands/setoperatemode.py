"""
SetOperateMode command class for DishLeafNode.
"""
from __future__ import annotations

import logging
from typing import Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import TimeKeeper
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class SetOperateMode(DishLNCommand):
    """
    A class for DishLeafNode's SetOperateMode() command.

    SetOperateMode invokes SetOperateMode command on Dish Master device.

    """

    def __init__(
        self: SetOperateMode,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
        is_configure_command: bool = False,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.is_configure_command = is_configure_command
        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, logger
        )

    # pylint: disable=unused-argument
    @timeout_tracker
    @error_propagation_tracker(
        "get_set_operate_mode_result_code", [ResultCode.OK]
    )
    def set_operate_mode(
        self: SetOperateMode, **kwargs
    ) -> Tuple[ResultCode, str]:
        """A method to invoke the SetOperateMode command.

        :return: A tuple containing the result code and a message.
        :rtype: Tuple[ResultCode, str]
        """
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        if self.is_configure_command is False:
            self.set_command_id(__class__.__name__)
        else:
            self.component_manager.command_in_progress = "Configure"

        return self.do()

    # pylint: disable=arguments-differ
    def do(self: SetOperateMode) -> Tuple[ResultCode, str]:
        """
        Method to invoke SetOperateMode command on DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """
        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter for device : %s is not found",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        with self.component_manager.tango_operation_execution_lock:
            self.logger.debug("Acquired  tango lock")
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "SetOperateMode"
            )

        self.logger.debug("Released tango lock")
        return result_code[0], message[0]
