"""This module provides base command class for DishLeafNode."""
from __future__ import annotations

import logging
import time
from operator import methodcaller
from typing import TYPE_CHECKING, Any

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
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

    def set_wait_for_dishmode(self: DishLNCommand, dishmode: DishMode) -> str:
        """Waits for transition of DishMode to the correct state.

        :return: True if the DishMode transitions to the correct state within
            the timeout period,False otherwise.
        :rtype: boolean
        """
        start_time = time.time()
        elapsed_time = 0
        flag = "NOT_ACHIEVED"
        while elapsed_time < self.component_manager.command_timeout:
            if self.component_manager.abort_event.is_set():
                self.component_manager.abort_event.clear()
                self.logger.info("Abort event is cleared")
                flag = "ABORTED"
                return flag
            if self.component_manager.dishMode == dishmode:
                flag = "ACHIEVED"
                return flag
            elapsed_time = time.time() - start_time

        self.logger.info(
            "Current Dishmode is %s", self.component_manager.dishMode
        )
        return flag

    def set_wait_for_configured_band(
        self: DishLNCommand, configured_band: str
    ) -> str:
        """Waits for transition of configuredBand to the correct state.

        :return: True if the DishMode transitions to the correct state within
            the timeout period,False otherwise.
        :rtype: boolean
        """
        start_time = time.time()
        elapsed_time = 0
        flag = "NOT_ACHIEVED"
        while elapsed_time < self.component_manager.command_timeout:
            if self.component_manager.abort_event.is_set():
                self.component_manager.abort_event.clear()
                self.logger.info("Abort event is cleared")
                flag = "ABORTED"
                return flag
            if self.component_manager.dishConfiguredBand == configured_band:
                self.logger.info(
                    "Dish band %s is configured.", configured_band
                )
                return "ACHIEVED"
            elapsed_time = time.time() - start_time
        return "NOT_ACHIEVED"

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

    # pylint: disable=arguments-differ
    def check_device_state(
        self,
        state_function: str,
        state_to_achieve: Any,
        expected_state: list,
        command_id,
    ) -> bool:
        """
        Waits for expected state with or without
        transitional state. On expected state occurrence,
        it sets ResultCode to OK and stops the tracker thread.

        :param state_function: The function to determine the state of the
                        device. Should be accessible in the component_manager
        :type state_function: str

        :param state_to_achieve: A particular state that needs to be
                                achieved for command completion.

        :param expected_state: Expected state of the device in case of
                        successful command execution. It's a list containing
                            transitional obsState if it exists for a command.
        :return: boolean value indicating if the state change occurred or not
        """
        if self.partial_configure:
            result_code = methodcaller(state_function)(self.component_manager)

            # Check if the result match the expected value
            return result_code[0] == state_to_achieve

        dish_mode, pointing_state, result_code = methodcaller(state_function)(
            self.component_manager
        )

        (
            expected_dish_mode,
            expected_pointing_states,
            expected_result_code,
        ) = expected_state

        # Check if the results match the expected values
        return (
            dish_mode == expected_dish_mode
            and pointing_state in expected_pointing_states
            and result_code == expected_result_code
        )
