"""
SetOperateMode command class for DishLeafNode.
"""
from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetOperateMode(DishLNCommand):
    """
    A class for DishLeafNode's SetOperateMode() command.

    SetOperateMode invokes SetOperateMode command on Dish Master device.

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
        Method to invoke SetOperateMode command on DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """
        result = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetOperateMode"
        )
        return result
