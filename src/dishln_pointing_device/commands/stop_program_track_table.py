"""This module contains StopProgramTrackTable implementation.
"""

from ska_tango_base.commands import FastCommand, ResultCode


class StopProgramTrackTable(FastCommand):
    """This class contains StopProgramTrackTrable implementation"""

    def do(self, *args, **kwargs) -> None:
        """This method stops generation program track table."""
        return ResultCode.OK, "Command Completed"
