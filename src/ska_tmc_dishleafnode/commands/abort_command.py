"""
Abort command class for DishLeafNode.
"""
from logging import Logger

from ska_tango_base.commands import ResultCode
from ska_tmc_common.adapters import AdapterFactory

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand
from ska_tmc_dishleafnode.manager.component_manager import (
    DishLNComponentManager,
)


class Abort(DishLNCommand):
    """
    A class for DishLeafNode's Abort() command.
    Command to abort the Dish Master and bring it to its ABORTED state.
    """

    def __init__(
        self,
        component_manager: DishLNComponentManager,
        op_state_model,
        adapter_factory: AdapterFactory,
        logger: Logger,
    ):
        super().__init__(
            component_manager,
            op_state_model,
            adapter_factory,
            logger=logger,
        )

    def check_allowed(self):
        """
        Checks whether this command is allowed
        It checks that the device is in the right state
        to execute this command and that all the
        component needed for the operation are not unresponsive

        :return: True if this command is allowed

        :rtype: boolean
        """

        # dish manager allows abort in all the dish modes
        # and pointing states
        # DishMode/s & pointing state/s To be decided ....

        self.check_op_state("Abort")
        self.component_manager.check_device_responsive()

        return True

    # pylint: disable=arguments-differ
    def do(self):
        """
        Invokes AbortCommands command on the DishMaster.

        param argin:
            None

        return:
            None

        raises:
           Raises exception if fails to execute
           TrackStop command on DishMaster.

        """
        try:
            ret_code, message = self.init_adapter()

            if ret_code == ResultCode.FAILED:
                return ret_code, message

            result_code = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Abort"
            )
            self.logger.info("Abort command executed successfully.")

        except Exception as e:
            self.logger.exception(f"Command invocation failed: {e}")
            return self.generate_command_result(
                ResultCode.FAILED,
                f"""The invocation of the Abort command is failed
                on Dish Master Device {self.dish_master_adapter.dev_name}.
                Reason: Error in executing the Abort command on
                Dish Master: {self.component_manager.dish_dev_name}
                The command has NOT been executed.
                This device will continue with its current operation.""",
            )
        return result_code
