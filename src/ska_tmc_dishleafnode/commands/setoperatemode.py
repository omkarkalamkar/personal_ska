"""
SetOperateMode command class for DishLeafNode.
"""
from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetOperateMode(DishLNCommand):
    """
    A class for DishLeafNode's SetOperateMode() command.

    SetOperateMode invokes SetOperateMode command on Dish Master device.

    """

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
