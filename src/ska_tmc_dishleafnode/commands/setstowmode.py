"""
SetStowMode command class for DishLeafNode.
"""
from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetStowMode(DishLNCommand):
    """
    A class for DishleafNode's SetStowMode() command.

    SetStowMode command on DishLeafNode enables the telescope to perform
    further operations and observations. It Invokes SetStowMode command on
    Dish Leaf Node device.
    """

    def do(self, argin=None):
        """
        Method to invoke SetStowMode command on DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """
        result = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetStowMode"
        )
        return result
