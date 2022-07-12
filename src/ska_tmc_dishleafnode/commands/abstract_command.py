"""This module provides base command class for DishLeafNode."""
# pylint: disable=abstract-method
import time

from ska_tango_base.commands import ResultCode
from ska_tmc_common.adapters import AdapterFactory, AdapterType
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.tmc_command import TmcLeafNodeCommand
from tango import DevState


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
        self.init_adapter()

    def check_op_state(self, command_name):
        """Checks if the given command is allowed ib current operational
        state."""
        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            raise CommandNotAllowed(
                f"""The invocation of the {command_name} command on this
                device is not allowed.
                Reason: The current operational state is
                {self.op_state_model.op_state}.
                The command has NOT been executed.
                This device will continue with normal operation."""
            )

    def init_adapter(self):
        """Creates adapter for underlying Dish device."""
        dev_name = self.component_manager.dish_dev_name
        timeout = self.component_manager.timeout
        elapsed_time = 0
        start_time = time.time()
        try:
            while self.dish_master_adapter is None and elapsed_time < timeout:
                self.dish_master_adapter = (
                    self._adapter_factory.get_or_create_adapter(
                        dev_name, AdapterType.DISH
                    )
                )
                elapsed_time = time.time() - start_time
            if self.dish_master_adapter is None:
                return self.adapter_error_message_result(
                    self.component_manager.dish_dev_name,
                    "Failed to create adapter",
                )

        except Exception as e:
            return self.adapter_error_message_result(
                self.component_manager.dish_dev_name,
                e,
            )

        return ResultCode.OK, ""
