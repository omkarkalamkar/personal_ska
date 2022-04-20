from ska_tango_base.commands import ResultCode
from ska_tmc_common.adapters import AdapterFactory, AdapterType
from ska_tmc_common.exceptions import CommandNotAllowed, DeviceUnresponsive
from ska_tmc_common.tmc_command import TmcLeafNodeCommand
from tango import DevState


class DishLNCommand(TmcLeafNodeCommand):
    def __init__(
        self, target, op_state_model, adapter_factory=None, logger=None
    ):
        super().__init__(target, logger)
        self.op_state_model = op_state_model
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.dish_master_adapter = None
        self.init_adapter()

    def check_unresponsive(self):
        component_manager = self.target
        dev_info = component_manager.get_device()
        if dev_info is None or dev_info.unresponsive:
            raise DeviceUnresponsive(
                """The invocation of the command on this device is not allowed.
                Reason: Dish Master device is not available.
                The command has NOT been executed.
                This device will continue with normal operation."""
            )

    def check_op_state(self, command_name):
        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            raise CommandNotAllowed(
                """The invocation of the %s command on this device is not allowed.
                Reason: The current operational state is %s.
                The command has NOT been executed.
                This device will continue with normal operation.""",
                command_name,
                self.op_state_model.op_state,
            )

    def init_adapter(self):
        component_manager = self.target
        dev_name = component_manager.dish_dev_name
        dev_info = component_manager.get_device()
        try:
            if not dev_info.unresponsive:
                self.dish_master_adapter = (
                    self._adapter_factory.get_or_create_adapter(
                        dev_name, AdapterType.DISH
                    )
                )
        except Exception as e:
            return self.adapter_error_message_result(
                component_manager.dish_dev_name,
                e,
            )

        return ResultCode.OK, ""
