"""
Abort command class for DishLeafNode.
"""
from logging import Logger

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common.adapters import AdapterFactory
from ska_tmc_common.enum import PointingState
from ska_tmc_common.exceptions import InvalidObsStateError

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand
from ska_tmc_dishleafnode.manager.component_manager import (
    DishLNComponentManager,
)


class Abort(DishLNCommand):
    """
    A class for DishLeafNode's Abort() command.

    Command to abort the Dish Subarray and bring it to its ABORTED state.
    """

    def __init__(
        self,
        component_manager: DishLNComponentManager,
        op_state_model,
        adapter_factory: AdapterFactory,
        logger: Logger,
    ):
        super().__init__(component_manager=component_manager, logger=logger)
        self.op_state_model = op_state_model
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.component_manager = component_manager

    def check_allowed(self):
        """
        Checks whether this command is allowed
        It checks that the device is in the right state
        to execute this command and that all the
        component needed for the operation are not unresponsive

        :return: True if this command is allowed

        :rtype: boolean

        """

        """
        Currently Abort command is allowed for all the dish modes.
        To be decided .....
        """
        self.component_manager.check_device_responsive()
        self.component_manager.check_op_state("Abort")

        current_obs_state = self.component_manager.get_device().obs_state

        if current_obs_state not in (
            ObsState.RESOURCING,
            ObsState.CONFIGURING,
            ObsState.SCANNING,
            ObsState.IDLE,
            ObsState.READY,
        ):
            message = (
                "Abort command is not allowed in current observation"
                + "on device {}".format(self.component_manager.dish_dev_name)
                + "Reason: The current observation state for observation is"
                + "{}".format(current_obs_state)
                + 'The "Abort" command has NOT been executed. This device will'
                + "continue with normal operation."
            )
            raise InvalidObsStateError(message)

        return True

    def do(self):
        """
        Invokes TrackStop command on the DishMaster.

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
            if (
                self.component_manager.get_device().pointing_state
                is not PointingState.READY
            ):
                ret_code, message = self.call_adapter_method(
                    "Dish Master", self.dish_master_adapter, "AbortCommands"
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
        return ret_code, message
