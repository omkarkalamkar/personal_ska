from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tmc_common.op_state_model import TMCOpStateModel
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

    # ----------
    # Attributes
    # ----------

    commandExecuted = attribute(
        dtype=(("DevString",),),
        max_dim_x=4,
        max_dim_y=10000,
    )

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
                A tuple containing a return code and a string message indicating status.
                The message is for information purpose only.

            rtype:
                (ResultCode, str)
            """
            super().do()
            device = self.target
            device._build_state = "{},{},{}".format(
                release.name, release.version, release.description
            )
            device._version_id = release.version
            device.op_state_model.perform_action("component_on")
            device.component_manager.command_executor.add_command_execution(
                "0", "Init", ResultCode.OK, ""
            )
            return (ResultCode.OK, "")

    def always_executed_hook(self):
        pass

    def delete_device(self):
        # if the init is called more than once
        # I need to stop all threads
        if hasattr(self, "component_manager"):
            self.component_manager.stop()

    # ------------------
    # Attributes methods
    # ------------------

    def read_dishMasterDevName(self):
        """Returns the dishMasterDevName attribute value."""
        return self.component_manager._dish_dev_name

    def write_dishMasterDevName(self, value):
        """Set the dishMasterDevName attribute."""
        self.component_manager.update_device_info(value)

    def read_commandExecuted(self):
        """Return the commandExecuted attribute."""
        result = []
        for command_executed in reversed(
            self.component_manager.command_executor.command_executed
        ):
            single_result = [
                str(command_executed["Id"]),
                str(command_executed["Command"]),
                str(command_executed["ResultCode"]),
                str(command_executed["Message"]),
            ]
            result.append(single_result)
        return result

    # --------
    # Commands
    # --------

    @command()
    @DebugIt()
    def SetStowMode(self):
        """Invokes SetStowMode command on DishMaster."""
        handler = self.get_command_object("SetStowMode")
        if self.component_manager._command_executor.queue_full:
            message = """The invocation of the \"SetStowMode\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"SetStowMode\"  command has NOT been queued and will not be executed.
            This device will continue with normal operation."""
            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager._command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    @command()
    @DebugIt()
    def SetStandbyLPMode(self):
        """Invokes SetStandbyLPMode (i.e. Low Power State) command on DishMaster."""
        handler = self.get_command_object("SetStandbyLPMode")
        if self.component_manager._command_executor.queue_full:
            message = """The invocation of the \"SetStandbyLPMode\"command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"SetStandbyLPMode\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""
            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager._command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    @command()
    @DebugIt()
    def SetOperateMode(self):
        """Invokes SetOperateMode command on DishMaster."""
        handler = self.get_command_object("SetOperateMode")
        if self.component_manager._command_executor.queue_full:
            message = """The invocation of the \"SetOperateMode\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"SetOperateMode\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""
            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager._command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    @command()
    @DebugIt()
    def SetStandbyFPMode(self):
        """Invokes SetStandbyFPMode command on DishMaster (Standby-Full power) mode."""
        handler = self.get_command_object("SetStandbyFPMode")
        if self.component_manager._command_executor.queue_full:
            message = """The invocation of the \"SetStandbyFPMode\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"SetStandbyFPMode\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""
            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager._command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_Scan_allowed(self):
        """
        Checks whether this command is allowed to be run in the current device state.

        :return: True if this command is allowed to be run in current device state.
        :rtype: boolean
        """
        handler = self.get_command_object("Scan")
        return handler.check_allowed()

    @command(
        dtype_in="str",
        doc_in="Timestamp",
    )
    @DebugIt()
    def Scan(self, argin):
        """Invokes Scan command on DishMaster."""
        handler = self.get_command_object("Scan")
        if self.component_manager.command_executor.queue_full:
            message = """The invocation of the \"Scan\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"Scan\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""

            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler, argin
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_EndScan_allowed(self):
        """
        Checks whether this command is allowed to be run in the current device state.

        :return: True if this command is allowed to be run in current device state.
        :rtype: boolean
        """
        handler = self.get_command_object("EndScan")
        return handler.check_allowed()

    @command(
        dtype_in="str",
        doc_in="Timestamp",
    )
    @DebugIt()
    def EndScan(self, argin):
        """Invokes StopCapture command on DishMaster."""

        handler = self.get_command_object("EndScan")
        if self.component_manager.command_executor.queue_full:
            message = """The invocation of the \"EndScan\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"EndScan\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""

            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler, argin
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_Configure_allowed(self):
        """
        Checks whether this command is allowed to be run in the current device state.

        :return: True if this command is allowed to be run in current device state.
        :rtype: boolean
        """
        handler = self.get_command_object("Configure")
        return handler.check_allowed()

    @command(
        dtype_in="str",
        doc_in="Pointing parameters of Dish",
    )
    @DebugIt()
    def Configure(self, argin):
        """Configures the Dish by setting pointing coordinates for a given observation."""

        handler = self.get_command_object("Configure")
        if self.component_manager.command_executor.queue_full:
            message = """The invocation of the \"Configure\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"Configure\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""

            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler, argin
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_StartCapture_allowed(self):
        """
        Checks whether this command is allowed to be run in the current device state.

        :return: True if this command is allowed to be run in current device state.
        :rtype: boolean
        """
        handler = self.get_command_object("StartCapture")
        return handler.check_allowed()

    @command(
        dtype_in="str",
        doc_in="The timestamp indicates the time, in UTC, at which command execution should start.",
    )
    @DebugIt()
    def StartCapture(self, argin):
        """Triggers the DishMaster to start data capturing on the configured band."""

        handler = self.get_command_object("StartCapture")
        if self.component_manager.command_executor.queue_full:
            message = """The invocation of the \"StartCapture\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"StartCapture\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""

            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler, argin
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_StopCapture_allowed(self):
        """
        Checks whether this command is allowed to be run in the current device state.

        :return: True if this command is allowed to be run in current device state.
        :rtype: boolean
        """
        handler = self.get_command_object("StopCapture")
        return handler.check_allowed()

    @command(
        dtype_in="str",
        doc_in="The timestamp indicates the time, in UTC, at which command execution should start.",
    )
    @DebugIt()
    def StopCapture(self, argin):
        """Invokes StopCapture command on DishMaster on the set configured band."""
        handler = self.get_command_object("StopCapture")
        if self.component_manager.command_executor.queue_full:
            message = """The invocation of the \"StopCapture\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"StopCapture\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""

            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler, argin
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_Track_allowed(self):
        """
        Checks whether this command is allowed to be run in the current device state.

        :return: True if this command is allowed to be run in current device state.
        :rtype: boolean
        """
        handler = self.get_command_object("Track")
        return handler.check_allowed()

    @command(
        dtype_in="str",
        doc_in="The JSON input string contains dish and pointing information.",
    )
    @DebugIt()
    def Track(self, argin):
        """Invokes Track command on the DishMaster."""
        handler = self.get_command_object("Track")
        if self.component_manager.command_executor.queue_full:
            message = """The invocation of the \"Track\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"Track\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""

            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler, argin
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_StopTrack_allowed(self):
        """
        Checks whether this command is allowed to be run in the current device state.

        :return: True if this command is allowed to be run in current device state.
        :rtype: boolean
        """
        handler = self.get_command_object("StopTrack")
        return handler.check_allowed()

    @command()
    @DebugIt()
    def StopTrack(self):
        """Invokes StopTrack command on the DishMaster."""
        handler = self.get_command_object("StopTrack")
        if self.component_manager.command_executor.queue_full:
            message = """The invocation of the \"StopTrack\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"StopTrack\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""

            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_Abort_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state

        :return: True if this command is allowed to be run in current device state
        :rtype: boolean
        """
        handler = self.get_command_object("Abort")
        return handler.check_allowed()

    @command()
    @DebugIt()
    def Abort(self):
        """Invokes Abort command on the DishMaster."""
        handler = self.get_command_object("Abort")
        if self.component_manager.command_executor.queue_full:
            message = """The invocation of the \"Abort\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"Abort\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""

            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_Restart_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state

        :return: True if this command is allowed to be run in current device state
        :rtype: boolean
        """
        handler = self.get_command_object("Restart")
        return handler.check_allowed()

    @command()
    @DebugIt()
    def Restart(self):
        """Invokes Restart command on the DishMaster."""
        handler = self.get_command_object("Restart")
        if self.component_manager.command_executor.queue_full:
            message = """The invocation of the \"Restart\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"Restart\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""

            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_ObsReset_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state

        :return: True if this command is allowed to be run in current device state
        :rtype: boolean
        """
        handler = self.get_command_object("ObsReset")
        return handler.check_allowed()

    @command()
    @DebugIt()
    def ObsReset(self):
        """Invokes ObsReset command on the DishLeafNode."""
        handler = self.get_command_object("ObsReset")
        if self.component_manager.command_executor.queue_full:
            message = """The invocation of the \"ObsReset\" command on this device failed.
            Reason: The command executor rejected the queuing of the command because its queue is full.
            The \"ObsReset\" command has NOT been queued and will not be executed.
            This device will continue with normal operation."""

            return [[ResultCode.FAILED], [message]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        cm = DishLNComponentManager(
            self.DishMasterFQDN,
            self.op_state_model,
            logger=self.logger,
            sleep_time=self.SleepTime,
        )
        return cm


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
