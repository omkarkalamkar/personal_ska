"""
SetStandbyLPMode command class for DishLeafNode.
"""
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetStandbyLPMode(DishLNCommand):
    """
    A class for DishLeafNode's SetStandbyLPMode() command.

    Invokes SetStandbyLPMode (i.e. Low Power State) command on DishMaster.

    """

    def check_allowed(self):
        """
        Checks whether this command is allowed. It checks that the device is in the right state
        to execute this command and that all the component needed for the operation are not
        unresponsive.

        :return: True if this command is allowed

        :rtype: boolean

        """
        self.check_op_state(__class__.__name__)
        self.check_unresponsive()
        return True

    def do(self, argin=None):
        """
        Method to invoke SetStandbyLPMode (Low power mode) command on DishMaster.

        param argin:
            None

        return:
            None

        raises:
            Exception If error occurs while invoking SetStandbyLPMode command on DishMaster.
        """

        log_msg = f"Invoking SetStandbyLPMode command on:{self.dish_master_adapter.dev_name}"
        self.logger.info(log_msg)

        try:
            self.dish_master_adapter.SetStandbyLPMode()
        except Exception as e:
            self.logger.exception("Command invocation failed: %s", e)
            return self.generate_command_result(
                ResultCode.FAILED,
                f"""The invocation of the SetStandbyLPMode command is failed on Dish Master Device {self.dish_master_adapter.dev_name}.
                Reason: Error in calling the SetStandbyLPMode command on Dish Master Device.
                The command has NOT been executed.
                This device will continue with normal operation.""",
            )
        log_msg = f"SetStandbyLPMode command successfully invoked on:{self.dish_master_adapter.dev_name}"
        self.logger.info(log_msg)
        return (ResultCode.OK, "")
