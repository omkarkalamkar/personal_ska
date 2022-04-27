"""
SetStowMode command class for DishLeafNode.
"""
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetStowMode(DishLNCommand):
    """
    A class for DishleafNode's SetStowMode() command.

    SetStowMode command on DishLeafNode enables the telescope to perform further operations
    and observations. It Invokes SetStowMode command on Dish Leaf Node device.
    """

    def check_allowed(self):
        """
        Checks whether this command is allowed. It checks that the device is in the right state
        to execute this command and that all the component needed for the operation are
        not unresponsive

        :return: True if this command is allowed

        :rtype: boolean

        """
        self.check_op_state(__class__.__name__)
        self.check_unresponsive()
        return True

    def do(self, argin=None):
        """
        Method to invoke SetStowMode command on DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """
        self.logger.info(
            f"Invoking SetStowMode command on: {self.dish_master_adapter.dev_name}"
        )
        try:
            self.dish_master_adapter.SetStowMode()
        except Exception as e:
            log_msg = f"""Execution of SetStowMode command is failed.
                       Reason: Error in calling SetStowMode command on {self.dish_master_adapter.dev_name}: {e}
                       The command is not executed successfully.
                       The device will continue with normal operation"""
            self.logger.exception(log_msg)
            return self.generate_command_result(
                ResultCode.FAILED,
                f"Error in calling SetStowMode command on {self.dish_master_adapter.dev_name}",
            )

        log_msg = f"SetStowMode command successfully invoked on:{self.dish_master_adapter.dev_name}"
        self.logger.info(log_msg)
        return (ResultCode.OK, "")
