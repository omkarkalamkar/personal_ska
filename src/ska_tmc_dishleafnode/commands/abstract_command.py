"""This module provides base command class for DishLeafNode."""
# pylint: disable=abstract-method
import time

from ska_tango_base.commands import ResultCode
from ska_tmc_common.adapters import AdapterFactory, AdapterType
from ska_tmc_common.tmc_command import TmcLeafNodeCommand
from tango import ConnectionFailed, DevFailed


class DishLNCommand(TmcLeafNodeCommand):
    """A base command class for DishLeafNode with the methods and parameters
    common across all the commands."""

    def __init__(
        self,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger=None,
    ):
        super().__init__(component_manager, logger)
        self.op_state_model = op_state_model
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.dish_master_adapter = None

    def init_adapter(self):
        """Creates adapter for underlying Dish device."""
        dev_name = self.component_manager.dish_dev_name
        timeout = self.component_manager.timeout
        elapsed_time = 0
        start_time = time.time()

        while self.dish_master_adapter is None and elapsed_time <=timeout:
            try:
                self.dish_master_adapter = (
                    self._adapter_factory.get_or_create_adapter(
                        dev_name, AdapterType.DISH
                    )
                )
            except ConnectionFailed as cf:
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    return self.adapter_error_message_result(
                        self.component_manager.dish_dev_name,
                        cf,
                    )
            except DevFailed as df:
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    return self.adapter_error_message_result(
                        self.component_manager.dish_dev_name,
                        df,
                    )

            except Exception as e:
                return self.adapter_error_message_result(
                    self.component_manager.dish_dev_name,
                    e,
                )

        return ResultCode.OK, ""
