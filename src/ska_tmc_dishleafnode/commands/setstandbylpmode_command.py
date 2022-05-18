"""
SetStandbyLPMode command class for DishLeafNode.
"""

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

        adapter = self.dish_master_adapter
        result = self.call_adapter_method(
            "Dish Master", adapter, "SetStandbyLPMode"
        )
        return result