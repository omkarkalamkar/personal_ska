""" A DishLeaf Node pointing device."""

from typing import List, Tuple

from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from tango import ArgType, AttrDataFormat, AttrWriteType
from tango.server import attribute, command, run

from ska_tmc_dishleafnode.dishln_pointing_device import (
    DishlnPointingDataComponentManager,
)


class DishPointingDevice(SKABaseDevice):
    """
    This class is responsible for doing the pointing calculations,
    forward transform and generating the programTrackTable

    :Device Properties:
    :Device Attributes:
    :commandExecuted: Stores command executed on the device.
    :DishlnPointingDeviceFQDN: Stores Dish leaf node pointing device name.
    """

    def init_device(self: SKABaseDevice) -> None:
        super().init_device()
        self._health_state = HealthState.OK
        self.dev_name = self.get_name()

    class InitCommand(SKABaseDevice.InitCommand):
        """A class for the DishPointingDevice's init_device() command."""

        # pylint: disable=W0221
        def do(self) -> Tuple[ResultCode, str]:
            """Change device state to INIT."""
            super().do()
            return (ResultCode.OK, "DishPointingDevice Initialized")

    def create_component_manager(self) -> DishlnPointingDataComponentManager:
        """
        Creates an instance of DishlnPointingDataComponentManager
        :return: component manager instance
        :rtype: DishlnPointingDataComponentManager
        """
        dish_pointing_device_component_manager = (
            DishlnPointingDataComponentManager(
                logger=self.logger,
            )
        )
        return dish_pointing_device_component_manager

    @attribute(
        dtype=ArgType.DevString,
        dformat=AttrDataFormat.SCALAR,
        access=AttrWriteType.READ,
    )
    def dishlnPointingDeviceFqdn(self) -> str:
        """
        This attribute is used for storing the FQDN of Dish leaf node pointing
        device.
        :return: str
        """
        return self.dev_name

    @command(
        dtype_in="DevVoid",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def GenerateProgramTrackTable(self) -> Tuple[List[ResultCode], List[str]]:
        """
        This command instructs dish pointing device to start generating program
        track table.

        :return: ResultCode and message
        :rtype: Tuple[List[ResultCode], List[str]]
        """

        self.logger.info(
            "GenerateProgramTrackTable command executed successfully"
        )
        return ([ResultCode.OK], ["Command Completed"])


def main(args=None, **kwargs):
    """
    Runs the DishPointingDevice Tango device.
    :param args: Arguments internal to TANGO

    :param kwargs: Arguments internal to TANGO

    :return: integer. Exit code of the run method.
    """
    return run((DishPointingDevice,), args=args, **kwargs)


if __name__ == "__main__":
    main()
