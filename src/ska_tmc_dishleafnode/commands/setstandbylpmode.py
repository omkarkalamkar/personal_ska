"""
SetStandbyLPMode command class for DishLeafNode.
"""

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetStandbyLPMode(DishLNCommand):
    """
    A class for DishLeafNode's SetStandbyLPMode() command.

    Invokes SetStandbyLPMode (i.e. Low Power State) command on DishMaster.

    """

    def do(self, argin=None):
        """
        Method to invoke SetStandbyLPMode (Low power mode) command on
        DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """

        result = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetStandbyLPMode"
        )
        return result
