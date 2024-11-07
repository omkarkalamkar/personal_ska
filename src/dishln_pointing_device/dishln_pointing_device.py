""" A DishLeaf Node pointing device."""

from typing import List, Tuple

from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tango_base.control_model import HealthState
from ska_tmc_common.tmc_base_leaf_device import TMCBaseLeafDevice
from tango import ArgType, AttrDataFormat, AttrWriteType
from tango.server import attribute, command, run

from dishln_pointing_device import DishlnPointingDataComponentManager


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
    def storeTargetData(self) -> str:
        """
        This attribute is used for storing the target data.
        device.
        :return: str
        """
        return self.component_manager.target_data

    @storeTargetData.write
    def storeTargetData(self, target_data: str) -> None:
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
        return self.pointing_program_track_table

    def update_pointing_program_track_table_callback(
        self, pointing_program_track_table: dict
    ) -> None:
        """This method helps in pushing event of program track table change.

        Args:
            pointing_program_track_table (dict): data of program track table.
        """
        self.pointing_program_track_table = pointing_program_track_table
        self.push_change_archive_events(
            "pointingProgramTrackTable", pointing_program_track_table
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

        self.logger.info(
            "GenerateProgramTrackTable command executed successfully"
        )
        return ([ResultCode.OK], ["Command Completed"])

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

        self.logger.info("StopProgramTrackTable command executed successfully")
        return ([ResultCode.OK], ["Command Completed"])

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
        for command_name, method_name in [
            (
                "GenerateProgramTrackTable",
                "generate_program_track_table",
                "StopProgramTrackTable",
                "stop_program_track_table",
            ),
        ]:
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name,
                    self._command_tracker,
                    self.component_manager,
                    method_name,
                    logger=self.logger,
                ),
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
