"""
SetStandbyFPMode command class for DishLeafNode.
"""
from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class SetStandbyFPMode(DishLNCommand):
    """
    A class for DishLeafNode's SetStandbyFPMode() command.

    Invokes SetStandbyFPMode (i.e. Full Power State) command on DishMaster.

    """

    def check_allowed(self):
        """
        Checks whether this command is allowed. It checks that the device is
        in the right state to execute this command and that all the component
        needed for the operation are not unresponsive

        :return: True if this command is allowed

        :rtype: boolean

        """
        self.check_op_state(__class__.__name__)
        return True

    def do(self, argin=None):
        """
        Method to invoke SetStandbyFPMode command on DishMaster.

        param argin:
            None

        return:
            (ResultCode, str)
        """

        adapter = self.dish_master_adapter
        result = self.call_adapter_method(
            "Dish Master", adapter, "SetStandbyFPMode"
        )
        return result
