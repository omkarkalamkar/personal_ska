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
        Checks whether this command is allowed. It checks that the device is
        in the right state to execute this command and that all the component
        needed for the operation are not unresponsive.

        :return: True if this command is allowed

        :rtype: boolean

        """
        self.check_op_state(__class__.__name__)
        return True

    def do(self, argin=None):
        """
        Method to invoke SetStandbyLPMode (Low power mode) command on
        DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """

        log_msg = f"""Invoking SetStandbyLPMode command on:
        {self.dish_master_adapter.dev_name}"""
        self.logger.info(log_msg)

        try:
            self.dish_master_adapter.SetStandbyLPMode()
        except Exception as e:
            log_msg = f"""Execution of SetStandbyLPMode command is failed.
                       Reason: Error in calling SetStandbyLPMode command on
                       {self.dish_master_adapter.dev_name}: {e}
                       The command is not executed successfully.
                       The device will continue with normal operation"""
            self.logger.exception(log_msg)
            return self.generate_command_result(
                ResultCode.FAILED,
                f"""Error in calling SetStandbyLPMode command on:
                {self.dish_master_adapter.dev_name}""",
            )
        log_msg = f"""SetStandbyLPMode command successfully invoked on:
        {self.dish_master_adapter.dev_name}"""
        self.logger.info(log_msg)
        return (ResultCode.OK, "")
