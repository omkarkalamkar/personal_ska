"""
SetOperateMode command class for DishLeafNode.
"""
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetOperateMode(DishLNCommand):
    """
    A class for DishLeafNode's SetOperateMode() command.

    SetOperateMode invokes SetOperateMode command on Dish Master device.

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
        Method to invoke SetOperateMode command on DishMaster.

        param argin:
            None

        return:
            None

        raises:
            Exception If error occurs while invoking SetOperateMode command on DishMaster.
        """
        self.logger.info(
            f"Invoking SetOperateMode command on: {self.dish_master_adapter.dev_name}"
        )
        try:
            self.dish_master_adapter.SetOperateMode()
        except Exception as e:
            self.logger.exception(e)
            return self.generate_command_result(
                ResultCode.FAILED,
                f"""The invocation of the SetOperateMode command is failed on
                Dish Master Device {self.dish_master_adapter.dev_name}.
                This device will continue with normal operation.""",
            )

        log_message = f"SetOperateMode command is successfully invoked on {self.dish_master_adapter.dev_name}."
        self.logger.info(log_message)
        return (ResultCode.OK, "")
