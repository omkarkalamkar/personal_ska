""" A DishLeaf Node pointing device."""

import json
from typing import List, Tuple

from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from ska_tmc_common.v1.tmc_base_leaf_device import TMCBaseLeafDevice
from tango import ArgType, AttrDataFormat, AttrWriteType, DevState
from tango.server import attribute, command, device_property, run

from ska_dishln_pointing_device import DishlnPointingDataComponentManager
from ska_dishln_pointing_device.commands.generate_program_track_table import (
    GenerateProgramTrackTable,
)
from ska_dishln_pointing_device.commands.stop_program_track_table import (
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

    # Dish Track command properties
    ElevationMaxLimit = device_property(dtype="DevFloat", default_value=90.0)
    ElevationMinLimit = device_property(dtype="DevFloat", default_value=15.0)
    TrackTableUpdateRate = device_property(
        dtype="DevFloat",
        default_value=50,
        doc="The rate at which a tracktable is provided. It is one"
        + "tracktable per specified number of seconds.",
    )
    TrackTableInAdvance = device_property(
        dtype="DevFloat",
        default_value=6,
        doc="programTrackTable in advance in seconds",
    )
    AzimuthMinLimit = device_property(
        dtype="DevFloat",
        default_value=-270.0,
        doc="Minimum value of Azimuth where dish can point",
    )

    AzimuthMaxLimit = device_property(
        dtype="DevFloat",
        default_value=270.0,
        doc="Maximum value of Azimuth where dish can point",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pointing_program_track_table: list = []
        self.program_track_table_error: str = ""
        self._update_state(DevState.ON)

    def init_device(self: SKABaseDevice) -> None:
        super().init_device()
        self._health_state = HealthState.OK
        self.dev_name = self.get_name()
        self.set_change_event("pointingProgramTrackTable", True, False)
        self.set_archive_event("pointingProgramTrackTable", True)
        self.set_change_event("programTrackTableError", True, False)
        self.set_archive_event("programTrackTableError", True)

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

    @attribute(dtype=str, access=AttrWriteType.READ)
    def programTrackTableError(self) -> str:
        """
        This attribute is used for storing error
        occurred during program track table calculation
        :return: str
        """
        return self.program_track_table_error

    @attribute(dtype=str, access=AttrWriteType.READ_WRITE)
    def targetData(self) -> str:
        """
        This attribute is used for storing the target data.
        :return: str
        """
        return json.dumps(self.component_manager.target_data)

    @targetData.write
    def targetData(self, target_data: str) -> None:
        """This method writes the attribute data in component manager.

        Args:
            target_data (str): _description_
        """
        self.component_manager.target_data = json.loads(target_data)

    @attribute(
        dtype=ArgType.DevString,
        dformat=AttrDataFormat.SCALAR,
        access=AttrWriteType.READ,
    )
    def pointingProgramTrackTable(self) -> str:
        """
        This attribute is used for storing calculated tracktable.
        :return: str
        """
        return json.dumps(self.pointing_program_track_table)

    def update_pointing_program_track_table_callback(
        self, pointing_program_track_table: list
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

    def update_program_track_table_error_callback(
        self, program_track_table_error: str
    ) -> None:
        """This method helps in pushing event of program track table error.
        :param program_track_table_error: program track table error.
        """
        self.program_track_table_error = program_track_table_error
        self.push_change_archive_events(
            "programTrackTableError",
            program_track_table_error,
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
        This command instructs to change current pointing/offset.

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
                disln_pointing_device_name=self.get_name(),
                logger=self.logger,
                update_pointing_program_track_table_callback=(
                    self.update_pointing_program_track_table_callback
                ),
                update_program_track_table_error_callback=(
                    self.update_program_track_table_error_callback
                ),
                track_table_update_rate=self.TrackTableUpdateRate,
                elevation_max_limit=self.ElevationMaxLimit,
                elevation_min_limit=self.ElevationMinLimit,
                track_table_advance_sec=self.TrackTableInAdvance,
                azimuth_min_limit=self.AzimuthMinLimit,
                azimuth_max_limit=self.AzimuthMaxLimit,
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
            GenerateProgramTrackTable(self.logger, self.component_manager),
        )
        self.register_command_object(
            "StopProgramTrackTable",
            StopProgramTrackTable(self.logger, self.component_manager),
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
