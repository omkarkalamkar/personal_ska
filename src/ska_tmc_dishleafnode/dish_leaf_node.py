"""This is DishLeafNode TANGO device."""
# flake8: noqa

import json
from typing import List, Tuple

from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tmc_common.enum import LivelinessProbeType
from tango import AttrWriteType, Database, DebugIt
from tango.server import attribute, command, device_property, run

from ska_tmc_dishleafnode import release
from ska_tmc_dishleafnode.commands.abort_command import AbortCommands
from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue
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
    DishMasterFQDN = device_property(dtype="str", doc="FQDN of Dish Master Device")

    SleepTime = device_property(dtype="DevFloat", default_value=1)
    DishAvailabilityCheckTimeout = device_property(dtype="DevUShort", default_value=120)
    CommandTimeOut = device_property(dtype="DevFloat", default_value=15)
    AdapterTimeOut = device_property(dtype="DevFloat", default_value=2)
    # Dish Track command properties
    Elevation = device_property(dtype="DevFloat", default_value=30.0)
    Azimuth = device_property(dtype="DevFloat", default_value=0.0)
    ElevationMaxLimit = device_property(dtype="DevFloat", default_value=90.0)
    ElevationMinLimit = device_property(dtype="DevFloat", default_value=17.5)
    TrackTableEntries = device_property(
        dtype="DevShort", default_value=25, doc="Number of entries in programTrackTable"
    )
    PointingCalculationPeriod = device_property(
        dtype="DevShort",
        default_value=100,
        doc="Time difference between two consecutive entries of programTrackTable in milliseconds",
    )
    # ----------
    # Attributes
    # ----------

    dishMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    isSubsystemAvailable = attribute(
        dtype=bool,
        access=AttrWriteType.READ,
    )

    actualPointing = attribute(
        dtype=str,
        access=AttrWriteType.READ,
    )

    # ---------------
    # General methods
    # ---------------

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the TMC DishLeafNode init_device() method.
        """

        # pylint: disable=W0221
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
            device._isSubsystemAvailable = True
            device._dishln_name = device.get_name()
            device.set_change_event("healthState", True, False)
            device.set_change_event("isSubsystemAvailable", True, False)
            device.set_change_event("actualPointing", True, False)
            device.set_change_event("kValueValidationResult", True, False)
            device.op_state_model.perform_action("component_on")
            return (ResultCode.OK, "")

    def delete_device(self):
        # if the init is called more than once
        # I need to stop all threads
        if hasattr(self, "component_manager"):
            self.logger.info("Inside device destructor")
            # pylint: disable=unnecessary-dunder-call
            self.component_manager.__del__()
            # pylint: enable=unnecessary-dunder-call

    def update_availablity_callback(self, availablity):
        """Change event callback for isSubsystemAvailable"""
        self._isSubsystemAvailable = availablity
        self.push_change_event("isSubsystemAvailable", availablity)

    def pointing_callback(self, actual_pointing: list) -> None:
        """Push an event for the actualPointing attribute."""
        self.push_change_event("actualPointing", json.dumps(actual_pointing))

    def kvalue_validation_callback(self) -> None:
        """Push an event for the kValueValidationResult attribute."""
        self.push_change_event(
            "kValueValidationResult", str(int(self.component_manager.kValueValidationResult))
        )
        self.logger.info(
            "k-value validation result: ResultCode.%s",
            ResultCode(self.component_manager.kValueValidationResult).name,
        )

    # ------------------
    # Attributes methods
    # ------------------

    def read_dishMasterDevName(self):
        """Returns the dishMasterDevName attribute value."""
        return self.component_manager.dish_dev_name

    def write_dishMasterDevName(self, value):
        """Set the dishMasterDevName attribute."""
        self.component_manager.dish_dev_name = value

    def read_isSubsystemAvailable(self):
        """Read method for isSubsystemAvailable"""
        return self._isSubsystemAvailable

    def read_actualPointing(self) -> str:
        """Returns the actualPointing attribute value."""
        return json.dumps(self.component_manager.actual_pointing)

    @attribute(
        dtype="DevLong",
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
    )
    def kValue(self) -> int:
        """Returns the k-value attribute value."""
        return self.component_manager.kValue

    @kValue.write
    def kValue(self, k_value: int) -> None:
        """Set the dish k-value."""
        self.component_manager.kValue = k_value

    @attribute(
        dtype="str",
        access=AttrWriteType.READ,
    )
    def kValueValidationResult(self) -> str:
        """Read method to get the k-value validation result"""
        return str(int(self.component_manager.kValueValidationResult))

    # --------
    # Commands
    # --------

    def is_SetStowMode_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        dish mode.

        :return: True if this command is allowed to be run in current
        dish mode.

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
        dish mode.

        :return: True if this command is allowed to be run in current
        dish mode
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
        dish mode.

        :return: True if this command is allowed to be run in current
        dish mode.

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
        dish mode.

        :return: True if this command is allowed to be run in current
        dish mode.

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

    @command(
        dtype_in="DevString",
        doc_in="The scan_id in string",
        dtype_out="DevVarLongStringArray",
        doc_out="information-only string",
    )
    @DebugIt()
    def Scan(self, argin: str) -> tuple:
        """
        Invokes Scan command on DishMaster (Standby-Full power)
        mode

        :rtype: tuple
        """
        handler = self.get_command_object("Scan")
        result_code, unique_id = handler(argin)
        return [result_code], [str(unique_id)]

    def is_Scan_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        dish mode.

        :return: True if this command is allowed to be run in current
        dish mode.

        :rtype: boolean
        """
        return self.component_manager.is_scan_allowed()

    def is_EndScan_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        dish mode.

        :return: True if this command is allowed to be run in current
        dish mode.

        :rtype: boolean
        """
        return self.component_manager.is_endscan_allowed()

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def EndScan(self) -> tuple:
        """
        Invokes EndScan command on DishMaster (Standby-Full power)
        mode

        :rtype: tuple
        """
        handler = self.get_command_object("EndScan")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    def is_off_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return self.component_manager.is_off_allowed()

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Off(self) -> tuple:
        """
        Invokes On command on Dish Master.
        """
        handler = self.get_command_object("Off")
        result_code, unique_id = handler()
        return [result_code], [unique_id]

    def is_Configure_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        dish mode.

        :return: True if this command is allowed to be run in current
        dish mode.

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
        result_code, unique_id = handler(argin)
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
        return self.component_manager.is_track_allowed()

    @command(
        dtype_in="str",
        doc_in="The JSON input string contains dish and pointing information.",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def Track(self, argin) -> tuple:
        """Invokes Track command on the DishMaster."""

        handler = self.get_command_object("Track")
        result_code, unique_id = handler(argin)
        return [result_code], [unique_id]

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def TrackStop(self):
        """
        Invokes TrackStop command on DishMaster

        :rtype: tuple
        """
        handler = self.get_command_object("TrackStop")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    def is_TrackStop_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return self.component_manager.is_trackstop_allowed()

    @command(
        dtype_in="str",
        doc_in="The JSON input string containing cross elevation/elevation offsets.",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def TrackLoadStaticOff(self, argin: str) -> Tuple[List[ResultCode], List[str]]:
        """
        Invokes TrackLoadStaticOff command on DishMaster

        :rtype: tuple
        """
        handler = self.get_command_object("TrackLoadStaticOff")
        result_code, unique_id = handler(argin)

        return [result_code], [str(unique_id)]

    def is_TrackLoadStaticOff_allowed(self):
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
        device state.

        :rtype: boolean
        """
        return self.component_manager.is_trackloadstaticoff_allowed()

    def is_AbortCommands_allowed(self):
        """
        Checks whether this command is allowed to be run in current
        device state

        :return: True if this command is allowed to be run in current device
        state

        :rtype: boolean
        """
        return self.component_manager.is_abortcommands_allowed()

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def AbortCommands(self):
        """Invokes AbortCommands command on the DishMaster."""

        handler = self.get_command_object("AbortCommands")
        result_code, unique_id = handler()
        return [result_code], [unique_id]

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

    def is_SetKValue_allowed(self):
        """
        Checks whether this command is allowed to be run in current
        device state

        :return: True if this command is allowed to be run in current device
        state

        :rtype: boolean
        """
        return self.component_manager.is_set_kvalue_allowed()

    @command(
        dtype_in="DevLong",
        doc_in="The k number in range [1-2222]",
        dtype_out="DevVarLongStringArray",
        doc_out="information-only string",
    )
    @DebugIt()
    def SetKValue(self, k_value: int) -> Tuple[List[ResultCode], List[str]]:
        """Invokes SetKValue command on the DishMaster."""
        handler = self.get_command_object("SetKValue")
        result_code, unique_id = handler(k_value)
        if result_code == ResultCode.OK:
            db = Database()
            value = {"kValue": {"__value": [self.component_manager.kValue]}}
            db.put_device_attribute_property(self._dishln_name, value)
            value = db.get_device_attribute_property(self._dishln_name, "kValue")
            self.logger.info("k-value memorized successfully: %s", value)
            self.kvalue_validation_callback()
        return [result_code], [unique_id]

    def create_component_manager(self):
        cm = DishLNComponentManager(
            self.DishMasterFQDN,
            logger=self.logger,
            track_table_entries=self.TrackTableEntries,
            pointing_calculation_period=self.PointingCalculationPeriod,
            communication_state_callback=None,
            component_state_callback=None,
            pointing_callback=self.pointing_callback,
            kvalue_validation_callback=self.kvalue_validation_callback,
            _liveliness_probe=LivelinessProbeType.SINGLE_DEVICE,
            _event_receiver=True,
            sleep_time=self.SleepTime,
            dish_availability_check_timeout=self.DishAvailabilityCheckTimeout,
            adapter_timeout=self.AdapterTimeOut,
            command_timeout=self.CommandTimeOut,
            elevation=self.Elevation,
            azimuth=self.Azimuth,
            elevation_max_limit=self.ElevationMaxLimit,
            elevation_min_limit=self.ElevationMinLimit,
            _update_availablity_callback=self.update_availablity_callback,
        )
        return cm

    def init_command_objects(self):
        """
        Initializes the command handlers for commands supported by this device.
        """
        super().init_command_objects()
        for command_name, method_name in [
            ("SetStandbyFPMode", "setstandbyfpmode"),
            ("SetStandbyLPMode", "setstandbylpmode"),
            ("SetOperateMode", "setoperatemode"),
            ("SetStowMode", "setstowmode"),
            ("Configure", "configure"),
            ("Track", "track"),
            ("TrackStop", "trackstop"),
            ("Off", "off"),
            ("SetKValue", "SetKValue"),
            ("TrackLoadStaticOff", "track_load_static_off"),
            ("Scan", "scan"),
            ("EndScan", "endscan"),
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

        self.register_command_object(
            "AbortCommands",
            AbortCommands(self.component_manager, logger=self.logger),
        )
        self.register_command_object(
            "SetKValue",
            SetKValue(self.component_manager, logger=self.logger),
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
