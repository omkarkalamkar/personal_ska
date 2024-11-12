"""This module contains GenerateProgramTrackTable implementation.
"""
from ska_tango_base.commands import FastCommand, ResultCode


class GenerateProgramTrackTable(FastCommand):
    """This class contains GenerateProgramTrackTrable implementation"""

    def do(self, *args, **kwargs) -> None:
        """This method generates program track table."""
        return ResultCode.STARTED, "Generation Started"
