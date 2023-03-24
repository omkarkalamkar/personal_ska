"""This is DishLeafNode TANGO device."""
# pylint: disable=line-too-long, fixme
# flake8: noqa
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tmc_common.enum import LivelinessProbeType
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property, run

from ska_tmc_dishleafnode import release
from ska_tmc_dishleafnode.manager import DishLNComponentManager


class DishLeafNode(SKABaseDevice):
    """
    A Leaf control node for DishMaster.

    :Device Properties:

        DishMasterFQDN:
            FQDN of Dish Master Device


    :Device Attributes:

        commandExecuted:
            Stores command executed on the device.


        dishMasterDevName:
            Stores Dish Master Device name.
    """

    # -----------------
    # Device Properties
    # -----------------
    DishMasterFQDN = device_property(
        dtype="str", doc="FQDN of Dish Master Device"
    )

    SleepTime = device_property(dtype="DevFloat", default_value=1)
    TimeOut = device_property(dtype="DevFloat", default_value=2)
    # ----------
    # Attributes
    # ----------

    dishMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    # ---------------
    # General methods
    # ---------------

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the TMC DishLeafNode init_device() method.
        """

        def do(self):
            """
            Initializes the attributes and properties of the DishLeafNode.

            return:
                A tuple containing a return code and a string message
                indicating status. The message is for information purpose only.

            rtype:
                (ResultCode, str)
            """
            super().do()
            device = self._device
            device._build_state = f"""{release.name},{release.version},
            {release.description}"""
            device._version_id = release.version
            device.set_change_event("healthState", True, False)
            device.op_state_model.perform_action("component_on")
            return (ResultCode.OK, "")

    def delete_device(self):
        # if the init is called more than once
        # I need to stop all threads
        if hasattr(self, "component_manager"):
            self.component_manager.stop_event_receiver()
            self.component_manager.stop_liveliness_probe()

    # ------------------
    # Attributes methods
    # ------------------

    def read_dishMasterDevName(self):
        """Returns the dishMasterDevName attribute value."""
        return self.component_manager.dish_dev_name

    def write_dishMasterDevName(self, value):
        """Set the dishMasterDevName attribute."""
        self.component_manager.dish_dev_name = value

    # --------
    # Commands
    # --------

    def is_SetStowMode_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return self.component_manager.is_setstowmode_allowed()

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def SetStowMode(self):
        """Invokes SetStowMode command on DishMaster."""

        handler = self.get_command_object("SetStowMode")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    def is_SetStandbyLPMode_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return self.component_manager.is_setstandbylpmode_allowed()

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def SetStandbyLPMode(self):
        """Invokes SetStandbyLPMode command on DishMaster (Standby-Low power)
        mode."""
        handler = self.get_command_object("SetStandbyLPMode")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    def is_SetOperateMode_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return self.component_manager.is_setoperatemode_allowed()

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def SetOperateMode(self):
        """Invokes SetOperateMode command on DishMaster device."""
        handler = self.get_command_object("SetOperateMode")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    def is_SetStandbyFPMode_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return self.component_manager.is_setstandbyfpmode_allowed()

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def SetStandbyFPMode(self):
        """Invokes SetStandbyFPMode command on DishMaster (Standby-Full power)
        mode."""
        handler = self.get_command_object("SetStandbyFPMode")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    # pylint: disable-all
    def is_Scan_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return False

    @command(
        dtype_in="str",
        doc_in="""The timestamp indicates the time, in UTC, at which command
        execution should start.""",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def Scan(self):
        """Invokes Scan command on DishMaster."""

        return [
            [ResultCode.FAILED],
            ["Scan command will be refactored in later PI's"],
        ]

    def is_EndScan_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return False

    @command(
        dtype_in="str",
        doc_in="""The timestamp indicates the time, in UTC, at which command
        execution should start.""",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def EndScan(self):
        """Invokes StopCapture command on DishMaster."""

        return [
            [ResultCode.FAILED],
            ["EndScan command will be refactored in later PI's"],
        ]

    def is_Configure_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return self.component_manager.is_configure_allowed()

    @command(
        dtype_in="str",
        doc_in="The string in JSON format",
        dtype_out="DevVarLongStringArray",
        doc_out="information-only string",
    )
    @DebugIt()
    def Configure(self, argin) -> tuple:
        """
        Invokes Configure command on Dish Master.
        """
        handler = self.get_command_object("Configure")
        args = json.loads(argin)
        result_code, unique_id = handler(args)
        return [result_code], [unique_id]

    def is_StartCapture_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return False

    @command(
        dtype_in="str",
        doc_in="""The timestamp indicates the time, in UTC, at which command
        execution should start.""",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def StartCapture(self):
        """Triggers the DishMaster to start data capturing on the configured
        band."""

        return [
            [ResultCode.FAILED],
            ["StartCapture command will be refactored in later PI's"],
        ]

    def is_StopCapture_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return False

    @command(
        dtype_in="str",
        doc_in="""The timestamp indicates the time, in UTC, at which command
        execution should start.""",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def StopCapture(self):
        """Invokes StopCapture command on DishMaster on the set configured
        band."""

        return [
            [ResultCode.FAILED],
            ["StopCapture command will be refactored in later PI's"],
        ]

    def is_Track_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return False

    @command(
        dtype_in="str",
        doc_in="The JSON input string contains dish and pointing information.",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def Track(self):
        """Invokes Track command on the DishMaster."""

        return [
            [ResultCode.FAILED],
            ["Track command will be refactored in later PI's"],
        ]

    def is_StopTrack_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return False

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def StopTrack(self):
        """Invokes StopTrack command on the DishMaster."""

        return [
            [ResultCode.FAILED],
            ["StopTrack command will be refactored in later PI's"],
        ]

    def is_Abort_allowed(self):
        """
        Checks whether this command is allowed to be run in current
        device state

        :return: True if this command is allowed to be run in current device
        state

        :rtype: boolean
        """
        return False

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Abort(self):
        """Invokes Abort command on the DishMaster."""

        return [
            [ResultCode.FAILED],
            ["Abort command will be refactored in later PI's"],
        ]

    def is_Restart_allowed(self):
        """
        Checks whether this command is allowed to be run in current
        device state

        :return: True if this command is allowed to be run in current
        device state
        :rtype: boolean
        """
        return False

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Restart(self):
        """Invokes Restart command on the DishMaster."""

        return [
            [ResultCode.FAILED],
            ["Restart command will be refactored in later PI's"],
        ]

    def is_ObsReset_allowed(self):
        """
        Checks whether this command is allowed to be run in current
        device state

        :return: True if this command is allowed to be run in current
        device state

        :rtype: boolean
        """
        return False

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def ObsReset(self):
        """Invokes ObsReset command on the DishLeafNode."""

        return [
            [ResultCode.FAILED],
            ["ObsReset command will be refactored in later PI's"],
        ]

    def create_component_manager(self):
        cm = DishLNComponentManager(
            self.DishMasterFQDN,
            logger=self.logger,
            communication_state_callback=None,
            component_state_callback=None,
            _liveliness_probe=LivelinessProbeType.SINGLE_DEVICE,
            _event_receiver=True,
            sleep_time=self.SleepTime,
            timeout=self.TimeOut,
        )
        return cm

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()
        for (command_name, method_name) in [
            ("SetStandbyFPMode", "setstandbyfpmode"),
            ("SetStandbyLPMode", "setstandbylpmode"),
            ("SetOperateMode", "setoperatemode"),
            ("SetStowMode", "setstowmode"),
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


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """
    Runs the DishLeafNode.
    :param args: Arguments internal to TANGO
    :param kwargs: Arguments internal to TANGO
    :return: DishLeafNode TANGO object.

    """
    return run((DishLeafNode,), args=args, **kwargs)


if __name__ == "__main__":
    main()
