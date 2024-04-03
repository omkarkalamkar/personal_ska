"""This module provides base command class for DishLeafNode."""
import logging
import time

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


class DishLNCommand(TmcLeafNodeCommand):
    """A base command class for DishLeafNode with the methods and parameters
    common across all the commands."""

    def __init__(
        self,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(component_manager, logger)
        self.op_state_model = op_state_model
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.dish_master_adapter = None

    def init_adapter(self):
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
                self.logger.info("Adapter created successfully")
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

    def set_wait_for_dishmode(self, dishmode: DishMode) -> bool:
        """Waits for transition of DishMode to the correct state.

        Returns:
        bool: True if the DishMode transitions to the correct state within
              the timeout period,False otherwise."""
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

    def set_wait_for_configured_band(self, configured_band: str):
        """Waits for transition of configuredBand to the correct state.

        Returns:
            bool: True if the DishMode transitions to the correct state within
              the timeout period,False otherwise."""
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

    def init_adapter_mid(self):
        self.init_adapter()
