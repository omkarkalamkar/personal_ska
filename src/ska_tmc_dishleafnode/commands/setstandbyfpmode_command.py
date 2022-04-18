"""
SetStandbyFPMode command class for DishleafNode.
"""
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetStandbyFPMode(DishLNCommand):
    """
    A class for DishLeafNode's SetStandbyFPMode() command.

    Invokes SetStandbyFPMode (i.e. Full Power State) command on DishMaster.

    """

    def check_allowed(self):
        """
        Checks whether this command is allowed. It checks that the device is in the right state
        to execute this command and that all the component needed for the operation are not
        unresponsive

        :return: True if this command is allowed

        :rtype: boolean

        """
        self.check_op_state(__class__.__name__)
        self.check_unresponsive()
        return True

    def do(self, argin=None):
        """
        Method to invoke SetStandbyFPMode command on DishMaster.

        param argin:
            None

        return:
            None

        raises:
            Exception If error occurs while invoking SetStandbyFPMode command on DishMaster.
        """

        log_msg = f"Invoking SetStandbyFPMode command on:{self.dish_master_adapter.dev_name}"
        self.logger.info(log_msg)

        try:
            log_msg = (
                "Invoking SetStandbyFPMode command on Dish Master %s: ",
                self.dish_master_adapter.dev_name,
            )
            self.logger.debug(log_msg)
            self.dish_master_adapter.SetStandbyFPMode()

        except Exception as e:
            self.logger.exception("Command invocation failed: %s", e)
            return self.generate_command_result(
                ResultCode.FAILED,
                f"""The invocation of the SetStandbyFPMode command is failed on Dish Master Device {self.dish_master_adapter.dev_name}.
                Reason: Error in calling the SetStandbyFPMode command on Dish Master Device.
                The command has NOT been executed.
                This device will continue with normal operation.""",
            )
        log_msg = f"SetStandbyFPMode command successfully invoked on:{self.dish_master_adapter.dev_name}"
        self.logger.info(log_msg)
        return (ResultCode.OK, "")
