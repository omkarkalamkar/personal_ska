""" A DishLeaf Node pointing device."""

import json
from typing import List, Tuple

from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from ska_tmc_common.tmc_base_leaf_device import TMCBaseLeafDevice
from tango import ArgType, AttrDataFormat, AttrWriteType
from tango.server import attribute, command, run

from dishln_pointing_device import DishlnPointingDataComponentManager
from dishln_pointing_device.commands.generate_program_track_table import (
    GenerateProgramTrackTable,
)
from dishln_pointing_device.commands.stop_program_track_table import (
    StopProgramTrackTable,
)


class DishPointingDevice(TMCBaseLeafDevice):
    """
    This class is responsible for doing the pointing calculations,
    forward transform and generating the programTrackTable

    :Device Properties:
    :Device Attributes:
    :commandExecuted: Stores command executed on the device.
    :DishlnPointingDeviceFQDN: Stores Dish leaf node pointing device name.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pointing_program_track_table: dict = {}

    def init_device(self: SKABaseDevice) -> None:
        super().init_device()
        self._health_state = HealthState.OK
        self.dev_name = self.get_name()
        self.set_change_event("pointingProgramTrackTable", True, False)
        self.set_archive_event("pointingProgramTrackTable", True)

    class InitCommand(SKABaseDevice.InitCommand):
        """A class for the DishPointingDevice's init_device() command."""

        # pylint: disable=W0221
        def do(self) -> Tuple[ResultCode, str]:
            """Change device state to INIT."""
            super().do()
            return (ResultCode.OK, "DishPointingDevice Initialized")

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

    @attribute(dtype=str)
    def TargetData(self) -> str:
        """
        This attribute is used for storing the target data.
        device.
        :return: str
        """
        return self.component_manager.target_data

    @TargetData.write
    def TargetData(self, target_data: str) -> None:
        """This method writes the attribute data in component manager.

        Args:
            target_data (str): _description_
        """
        self.component_manager.target_data = target_data

    @attribute(
        dtype=ArgType.DevString,
        dformat=AttrDataFormat.SCALAR,
        access=AttrWriteType.READ,
    )
    def pointingProgramTrackTable(self) -> str:
        """
        This attribute is used for storing the FQDN of Dish leaf node pointing
        device.
        :return: str
        """
        return json.dumps(self.pointing_program_track_table)

    def update_pointing_program_track_table_callback(
        self, pointing_program_track_table: dict
    ) -> None:
        """This method helps in pushing event of program track table change.

        Args:
            pointing_program_track_table (dict): data of program track table.
        """
        self.pointing_program_track_table = pointing_program_track_table
        self.push_change_archive_events(
            "pointingProgramTrackTable",
            json.dumps(pointing_program_track_table),
        )

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
        handler = self.get_command_object("GenerateProgramTrackTable")
        result_code, message = handler()

        return [result_code], [message]

    @command(
        dtype_in="DevVoid",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def StopProgramTrackTable(self) -> Tuple[List[ResultCode], List[str]]:
        """
        This command instructs dish pointing device to stop generation of
        program track table.

        :return: ResultCode and message
        :rtype: Tuple[List[ResultCode], List[str]]
        """
        handler = self.get_command_object("StopProgramTrackTable")
        result_code, message = handler()

        return [result_code], [message]

    @command(
        dtype_in="DevString",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def ChangePointingData(
        self, argin: str | None = None
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        This command sets change pointing offset flag.

        :return: ResultCode and message
        :rtype: Tuple[List[ResultCode], List[str]]
        """
        self.logger.debug("Command invoked with argin %s", argin)
        return ([ResultCode.OK], ["offset change event set"])

    def create_component_manager(self) -> DishlnPointingDataComponentManager:
        """
        Creates an instance of DishlnPointingDataComponentManager
        :return: component manager instance
        :rtype: DishlnPointingDataComponentManager
        """
        dish_pointing_device_component_manager = (
            DishlnPointingDataComponentManager(
                self.logger,
                self.update_pointing_program_track_table_callback,
            )
        )
        return dish_pointing_device_component_manager

    def init_command_objects(self) -> None:
        """
        Initializes the command handlers for commands supported by this device.
        """
        super().init_command_objects()

        self.register_command_object(
            "GenerateProgramTrackTable",
            GenerateProgramTrackTable(self.logger),
        )
        self.register_command_object(
            "StopProgramTrackTable",
            StopProgramTrackTable(self.logger),
        )


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
