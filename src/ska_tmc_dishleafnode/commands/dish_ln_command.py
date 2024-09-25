"""This module provides base command class for DishLeafNode."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Dict, Tuple, Union

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import (
    AdapterFactory,
    AdapterType,
    DishMode,
    TmcLeafNodeCommand,
)
from tango import ConnectionFailed, DevFailed

configure_logging()
LOGGER = logging.getLogger(__name__)
if TYPE_CHECKING:
    from ..manager.component_manager import DishLNComponentManager


class DishLNCommand(TmcLeafNodeCommand):
    """A base command class for DishLeafNode with the methods and parameters
    common across all the commands."""

    def __init__(
        self: DishLNCommand,
        component_manager: DishLNComponentManager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(component_manager, logger)
        self.task_callback: TaskCallbackType
        self.op_state_model = op_state_model
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.dish_master_adapter = None
        self.partial_configure = False

    def init_adapter(self: DishLNCommand):
        """Creates adapter for underlying Dish device."""
        dev_name = self.component_manager.dish_dev_name
        timeout = self.component_manager.adapter_timeout
        elapsed_time = 0
        start_time = time.time()

        while self.dish_master_adapter is None and elapsed_time <= timeout:
            try:
                self.dish_master_adapter = (
                    self._adapter_factory.get_or_create_adapter(
                        dev_name, AdapterType.DISH
                    )
                )
                self.dish_master_adapter.proxy.set_timeout_millis(5000)
                self.logger.info("Adapter created successfully")
                self.component_manager.set_dish_adapter(
                    self.dish_master_adapter
                )
            except ConnectionFailed as connection_failed:
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    return (
                        ResultCode.FAILED,
                        str(connection_failed),
                    )
            except DevFailed as device_failed:
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    return (
                        ResultCode.FAILED,
                        str(device_failed),
                    )

            except (AttributeError, ValueError, TypeError) as exception:
                return (
                    ResultCode.FAILED,
                    str(exception),
                )

        return ResultCode.OK, ""

    def set_wait_for_dishmode(self: DishLNCommand, dishmode: DishMode) -> bool:
        """Waits for transition of DishMode to the correct state.

        :return: True if the DishMode transitions to the correct state within
            the timeout period,False otherwise.
        :rtype: boolean
        """
        start_time = time.time()
        elapsed_time = 0
        while elapsed_time < self.component_manager.command_timeout:
            if self.component_manager.dishMode == dishmode:
                return True
            elapsed_time = time.time() - start_time

        self.logger.info(
            "Current Dishmode is %s", self.component_manager.dishMode
        )
        return False

    def set_wait_for_configured_band(
        self: DishLNCommand, configured_band: str
    ):
        """Waits for transition of configuredBand to the correct state.

        :return: True if the DishMode transitions to the correct state within
            the timeout period,False otherwise.
        :rtype: boolean
        """
        start_time = time.time()
        elapsed_time = 0
        while elapsed_time < self.component_manager.command_timeout:
            if self.component_manager.dishConfiguredBand == configured_band:
                self.logger.info(
                    "Dish band %s is configured.", configured_band
                )
                return True
            elapsed_time = time.time() - start_time
        return False

    def init_adapter_mid(self: DishLNCommand):
        self.init_adapter()

    def set_command_id(self, command_name: str):
        """
        Sets the command id for error propagation.

        :param command_name: Name of the command
        :type command_name: str
        """
        command_id = f"{time.time()}-{command_name}"
        self.logger.info(
            "Setting command id as %s for command: %s",
            command_id,
            command_name,
        )
        self.component_manager.command_id = command_id

    def update_task_status(
        self,
        **kwargs: Dict[str, Union[Tuple[ResultCode, str], TaskStatus, str]],
    ) -> None:
        """
        Update the status of a task.

        Args:
            **kwargs: Keyword arguments for task status update.
        """
        result = kwargs.get("result")
        status = kwargs.get("status", TaskStatus.COMPLETED)
        message = kwargs.get("exception")
        if status == TaskStatus.ABORTED:
            self.task_callback(status=status)
        if result:
            if result[0] == ResultCode.FAILED:
                self.task_callback(
                    status=status, result=result, exception=message
                )
            else:
                self.logger.info("Result is: %s", result)
                self.task_callback(status=status, result=result)
        self.component_manager.command_in_progress = ""
        self.component_manager.reset_configure_command_result_values()
