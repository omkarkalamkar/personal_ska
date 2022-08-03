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


# Modified the tango device class to have Submitted slow command functionality
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
    # TODO: Refactor the below code to support base class v0.13.0
    # def is_SetStowMode_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in the current \
    #     device state. \

    #     :return: True if this command is allowed to be run in current \
    #     device state. \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("SetStowMode")
    #     return handler.check_allowed()

    # @command(dtype_out="DevVarLongStringArray")
    # @DebugIt()
    # def SetStowMode(self):
    #     """Invokes SetStowMode command on DishMaster."""
    #     handler = self.get_command_object("SetStowMode")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"SetStowMode\" command on this
    #         device failed. Reason: The command executor rejected the queuing
    #         of the command because its queue is full. The \"SetStowMode\"
    #         command has NOT been queued and will not be executed.
    #         This device will continue with normal operation."""
    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_SetStandbyLPMode_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("SetStandbyLPMode")

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def SetStandbyLPMode(self):
        """Invokes SetStandbyLPMode command on DishMaster (Standby-Low power)
        mode."""
        handler = self.get_command_object("SetStandbyLPMode")
        result_code, unique_id = handler()

        return [[result_code], [str(unique_id)]]

    # TODO: Refactor the below code to support base class v0.13.0
    # def is_SetOperateMode_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in the current \
    #     device state. \

    #     :return: True if this command is allowed to be run in current \
    #     device state. \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("SetOperateMode")
    #     return handler.check_allowed()

    # @command(dtype_out="DevVarLongStringArray")
    # @DebugIt()
    # def SetOperateMode(self):
    #     """Invokes SetOperateMode command on DishMaster."""
    #     handler = self.get_command_object("SetOperateMode")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"SetOperateMode\" command on
    #         this device failed. Reason: The command executor rejected the
    #         queuing of the command because its queue is full. The
    #         \"SetOperateMode\" command has NOT been queued and will not be
    #         executed. This device will continue with normal operation."""
    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_SetStandbyFPMode_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("SetStandbyFPMode")

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def SetStandbyFPMode(self):
        """Invokes SetStandbyFPMode command on DishMaster (Standby-Full power)
        mode."""
        handler = self.get_command_object("SetStandbyFPMode")
        result_code, unique_id = handler()

        return [[result_code], [str(unique_id)]]

    # TODO: Refactor the below code to support base class v0.13.0
    # def is_Scan_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in the current \
    #     device state. \

    #     :return: True if this command is allowed to be run in current \
    #     device state. \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("Scan")
    #     return handler.check_allowed()

    # @command(
    #     dtype_in="str",
    #     doc_in="Timestamp",
    #     dtype_out="DevVarLongStringArray",
    # )
    # @DebugIt()
    # def Scan(self, argin):
    #     """Invokes Scan command on DishMaster."""
    #     handler = self.get_command_object("Scan")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"Scan\" command on this device
    #         failed.
    #         Reason: The command executor rejected the queuing of the command
    #         because its queue is full.
    #         The \"Scan\" command has NOT been queued and will not be executed.
    #         This device will continue with normal operation."""

    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler, argin
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_EndScan_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in the current \
    #     device state. \

    #     :return: True if this command is allowed to be run in current \
    #     device state. \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("EndScan")
    #     return handler.check_allowed()

    # @command(
    #     dtype_in="str",
    #     doc_in="Timestamp",
    #     dtype_out="DevVarLongStringArray",
    # )
    # @DebugIt()
    # def EndScan(self, argin):
    #     """Invokes StopCapture command on DishMaster."""

    #     handler = self.get_command_object("EndScan")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"EndScan\" command on this
    #         device failed.
    #         Reason: The command executor rejected the queuing of the command
    #         because its queue is full.
    #         The \"EndScan\" command has NOT been queued and will not be
    #         executed.
    #         This device will continue with normal operation."""

    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler, argin
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_Configure_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in the current \
    #     device state. \

    #     :return: True if this command is allowed to be run in current \
    #     device state. \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("Configure")
    #     return handler.check_allowed()

    # @command(
    #     dtype_in="str",
    #     doc_in="Pointing parameters of Dish",
    #     dtype_out="DevVarLongStringArray",
    # )
    # @DebugIt()
    # def Configure(self, argin):
    #     """Configures the Dish by setting pointing coordinates for a given
    #     observation."""

    #     handler = self.get_command_object("Configure")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"Configure\" command on this
    #         device failed.
    #         Reason: The command executor rejected the queuing of the command
    #         because its queue is full.
    #         The \"Configure\" command has NOT been queued and will not be
    #         executed.

    #         This device will continue with normal operation."""

    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler, argin
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_StartCapture_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in the current \
    #     device state. \

    #     :return: True if this command is allowed to be run in current \
    #     device state. \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("StartCapture")
    #     return handler.check_allowed()

    # @command(
    #     dtype_in="str",
    #     doc_in="""The timestamp indicates the time, in UTC, at which command
    #     execution should start.""",
    #     dtype_out="DevVarLongStringArray",
    # )
    # @DebugIt()
    # def StartCapture(self, argin):
    #     """Triggers the DishMaster to start data capturing on the configured
    #     band."""

    #     handler = self.get_command_object("StartCapture")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"StartCapture\" command on
    #         this device failed.
    #         Reason: The command executor rejected the queuing of the command
    #         because its queue is full.
    #         The \"StartCapture\" command has NOT been queued and will not be
    #         executed. This device will continue with normal operation."""

    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler, argin
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_StopCapture_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in the current \
    #     device state. \

    #     :return: True if this command is allowed to be run in current \
    #     device state. \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("StopCapture")
    #     return handler.check_allowed()

    # @command(
    #     dtype_in="str",
    #     doc_in="""The timestamp indicates the time, in UTC, at which command
    #     execution should start.""",
    #     dtype_out="DevVarLongStringArray",
    # )
    # @DebugIt()
    # def StopCapture(self, argin):
    #     """Invokes StopCapture command on DishMaster on the set configured
    #     band."""
    #     handler = self.get_command_object("StopCapture")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"StopCapture\" command on this
    #         device failed.
    #         Reason: The command executor rejected the queuing of the command
    #         because its queue is full.
    #         The \"StopCapture\" command has NOT been queued and will not be
    #         executed. This device will continue with normal operation."""

    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler, argin
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_Track_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in the current \
    #     device state. \

    #     :return: True if this command is allowed to be run in current \
    #     device state. \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("Track")
    #     return handler.check_allowed()

    # @command(
    #     dtype_in="str",
    #     doc_in="The JSON input string contains dish and pointing information.",
    #     dtype_out="DevVarLongStringArray",
    # )
    # @DebugIt()
    # def Track(self, argin):
    #     """Invokes Track command on the DishMaster."""
    #     handler = self.get_command_object("Track")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"Track\" command on this
    #         device failed.
    #         Reason: The command executor rejected the queuing of the command
    #         because its queue is full.
    #         The \"Track\" command has NOT been queued and will not be executed.
    #         This device will continue with normal operation."""

    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler, argin
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_StopTrack_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in the current \
    #     device state. \

    #     :return: True if this command is allowed to be run in current \
    #     device state. \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("StopTrack")
    #     return handler.check_allowed()

    # @command(dtype_out="DevVarLongStringArray")
    # @DebugIt()
    # def StopTrack(self):
    #     """Invokes StopTrack command on the DishMaster."""
    #     handler = self.get_command_object("StopTrack")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"StopTrack\" command on this
    #         device failed.
    #         Reason: The command executor rejected the queuing of the command
    #         because its queue is full.
    #         The \"StopTrack\" command has NOT been queued and will not be
    #         executed.
    #         This device will continue with normal operation."""

    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_Abort_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current \
    #     device state \

    #     :return: True if this command is allowed to be run in current device \
    #     state \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("Abort")
    #     return handler.check_allowed()

    # @command(dtype_out="DevVarLongStringArray")
    # @DebugIt()
    # def Abort(self):
    #     """Invokes Abort command on the DishMaster."""
    #     handler = self.get_command_object("Abort")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"Abort\" command on this
    #         device failed.
    #         Reason: The command executor rejected the queuing of the command
    #         because its queue is full.
    #         The \"Abort\" command has NOT been queued and will not be executed.
    #         This device will continue with normal operation."""

    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_Restart_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current \
    #     device state \

    #     :return: True if this command is allowed to be run in current \
    #     device state \
    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("Restart")
    #     return handler.check_allowed()

    # @command(dtype_out="DevVarLongStringArray")
    # @DebugIt()
    # def Restart(self):
    #     """Invokes Restart command on the DishMaster."""
    #     handler = self.get_command_object("Restart")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"Restart\" command on this
    #         device failed.
    #         Reason: The command executor rejected the queuing of the command
    #         because its queue is full.
    #         The \"Restart\" command has NOT been queued and will not be
    #         executed. This device will continue with normal operation."""

    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_ObsReset_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current \
    #     device state \

    #     :return: True if this command is allowed to be run in current \
    #     device state \

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("ObsReset")
    #     return handler.check_allowed()

    # @command(dtype_out="DevVarLongStringArray")
    # @DebugIt()
    # def ObsReset(self):
    #     """Invokes ObsReset command on the DishLeafNode."""
    #     handler = self.get_command_object("ObsReset")
    #     if self.component_manager.command_executor.queue_full:
    #         message = """The invocation of the \"ObsReset\" command on this
    #         device failed.
    #         Reason: The command executor rejected the queuing of the command
    #         because its queue is full.
    #         The \"ObsReset\" command has NOT been queued and will not be
    #         executed. This device will continue with normal operation."""

    #         return [[ResultCode.FAILED], [message]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # TODO: Passing liveliness_probe as NONE throws an error.
    # Need to debug and solve it.
    def create_component_manager(self):
        cm = DishLNComponentManager(
            self.DishMasterFQDN,
            logger=self.logger,
            communication_state_callback=None,
            component_state_callback=None,
            _liveliness_probe=LivelinessProbeType.SINGLE_DEVICE,
            _event_receiver=False,
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
