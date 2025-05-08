"""This is DishLeafNode TANGO device."""
# flake8: noqa
from __future__ import annotations

import json
from typing import List, Tuple, Union

import tango
from numpy import isnan
from numpy import nan as NaN
from ska_control_model import HealthState
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tmc_common import (
    CommandNotAllowed,
    DeviceUnresponsive,
    DishMode,
    LivelinessProbeType,
    PointingState,
)
from ska_tmc_common.v1.tmc_base_leaf_device import TMCBaseLeafDevice
from tango import (
    ArgType,
    AttrDataFormat,
    AttrQuality,
    AttrWriteType,
    Database,
    DebugIt,
    TimeVal,
)
from tango.server import attribute, command, device_property, run

from ska_tmc_dishleafnode import release
from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue
from ska_tmc_dishleafnode.manager import DishLNComponentManager


# pylint: disable = attribute-defined-outside-init
class MidTmcLeafNodeDish(TMCBaseLeafDevice):
    """
    A Leaf control node for DishMaster.

    :Device Properties:
    :MidDishControl: FQDN of Dish Master Device
    :Device Attributes:
    :commandExecuted: Stores command executed on the device.
    :dishMasterDevName: Stores Dish Master Device name.
    """

    # -----------------
    # Device Properties
    # -----------------
    MidDishControl = device_property(
        dtype="str",
        doc="FQDN of Dish Master Device",
    )

    MidPointingDevice = device_property(
        dtype="str",
        doc="FQDN of DishLeaf Node Pointing Device",
    )
    DishAvailabilityCheckTimeout = device_property(
        dtype="DevUShort", default_value=3
    )
    CommandTimeOut = device_property(dtype="DevFloat", default_value=30)
    IsDishAbortEnabled = device_property(
        dtype="DevBoolean", default_value=False
    )

    # Dish Track command properties
    MaxTrackTableRetry = device_property(
        dtype="DevShort",
        default_value=3,
        doc="Maximum retries for the programTrackTable write operations",
    )
    TrackTableRetryDuration = device_property(
        dtype="DevFloat",
        default_value=0.2,
        doc="Retry duration for programTrackTable write operation in seconds",
    )

    # ----------
    # Attributes
    # ----------

    dishMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    dishlnPointingDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    trackTableErrors = attribute(
        dtype=("str",),
        max_dim_x=1024,
        access=AttrWriteType.READ,
    )

    isSubsystemAvailable = attribute(
        dtype=bool,
        access=AttrWriteType.READ,
    )

    actualPointing = attribute(
        dtype=str,
        access=AttrWriteType.READ,
    )

    dishMode = attribute(
        dtype=DishMode,
        access=AttrWriteType.READ,
    )

    pointingState = attribute(
        dtype=PointingState,
        access=AttrWriteType.READ,
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self: MidTmcLeafNodeDish):
        self._isSubsystemAvailable = True
        self._dishMode = DishMode.UNKNOWN
        self._pointingState = PointingState.NONE
        self._global_pointing_model_params = "{}"
        self._sdpQueueConnectorFqdn = ""
        self._sourceOffset: List = [NaN, NaN]
        self._lastPointingData: str = "Not Set"
        self._last_pointing_data_attr_quality = getattr(
            AttrQuality, "ATTR_VALID"
        )
        super().init_device()
        for attribute_name in [
            "healthState",
            "isSubsystemAvailable",
            "actualPointing",
            "dishMode",
            "kValueValidationResult",
            "pointingState",
            "sdpQueueConnectorFqdn",
            "sourceOffset",
            "lastPointingData",
            "kValue",
            "trackTableErrors",
            "globalPointingModelParams",
        ]:
            self.set_change_event(attribute_name, True, False)
            self.set_archive_event(attribute_name, True)

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the TMC DishLeafNode init_device() method.
        """

        # pylint: disable=W0221
        def do(self):
            """
            Initializes the attributes and properties of the
            MidTmcLeafNodeDish.

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
            device._dishln_name = device.get_name()
            device._update_health_state(HealthState.DEGRADED)
            device.op_state_model.perform_action("component_on")
            return (ResultCode.OK, "")

    def delete_device(self):
        # if the init is called more than once
        # I need to stop all threads
        if hasattr(self, "component_manager"):
            # pylint: disable=unnecessary-dunder-call
            self.component_manager.__del__()
            # pylint: enable=unnecessary-dunder-call

    def update_health_state_callback(self, healthState: HealthState) -> None:
        """Change event callback for sourceOffset attribute"""
        self._health_state = healthState
        with tango.EnsureOmniThread():
            self.push_change_archive_events("healthState", self._health_state)
        self.logger.info(
            "HealthState updated to value: %s", self._health_state
        )

    def update_source_offset_callback(self, source_offset: List) -> None:
        """Change event callback for sourceOffset attribute"""
        self._sourceOffset = source_offset
        with tango.EnsureOmniThread():
            self.push_change_archive_events("sourceOffset", self._sourceOffset)
        self.logger.info(
            "sourceOffset updated to value: %s", self._sourceOffset
        )

    def update_last_pointing_data_cb(self, last_pointing_data: List) -> None:
        """Change event callback for lastPointingData attribute"""
        if isnan(last_pointing_data).any():
            self._last_pointing_data_attr_quality = getattr(
                AttrQuality, "ATTR_ALARM"
            )
        else:
            self._last_pointing_data_attr_quality = getattr(
                AttrQuality, "ATTR_VALID"
            )
        self._lastPointingData = json.dumps(last_pointing_data.tolist())
        with tango.EnsureOmniThread():
            self.push_change_archive_events(
                "lastPointingData", self._lastPointingData
            )
        self.logger.info(
            "lastPointingData updated to value: %s", last_pointing_data
        )

    def update_availablity_callback(self, availability):
        """Change event callback for isSubsystemAvailable"""
        if self._isSubsystemAvailable != availability:
            self._isSubsystemAvailable = availability
            with tango.EnsureOmniThread():
                self.push_change_archive_events(
                    "isSubsystemAvailable", availability
                )

    def pointing_callback(self, actual_pointing: list) -> None:
        """Push an event for the actualPointing attribute."""
        with tango.EnsureOmniThread():
            self.push_change_archive_events(
                "actualPointing", json.dumps(actual_pointing)
            )

    def update_track_table_errors_callback(self, value: list) -> None:
        """Push an event for the trackTableErrors attribute."""
        self.logger.debug(
            "Track Table errors to be reported: %s",
            self.component_manager.errors_to_be_reported,
        )
        with tango.EnsureOmniThread():
            self.push_change_archive_events("trackTableErrors", value)
        self.logger.debug("Pushed the trackTableErrors event: %s", value)

    def update_global_pointing_param_callback(
        self, global_pointing_model_params: str
    ) -> None:
        """Push an event for the change of dishMode attribute."""
        self._global_pointing_model_params = global_pointing_model_params
        with tango.EnsureOmniThread():
            self.push_change_archive_events(
                "globalPointingModelParams",
                json.dumps(self._global_pointing_model_params),
            )

    def update_dishmode_callback(self, dish_mode: DishMode) -> None:
        """Push an event for the change of dishMode attribute."""
        self._dishMode = dish_mode
        with tango.EnsureOmniThread():
            self.push_change_archive_events("dishMode", self._dishMode)

    def update_pointingstate_callback(
        self, pointing_state: PointingState
    ) -> None:
        """Push an event for change of pointingState attribute."""
        self._pointingState = pointing_state
        with tango.EnsureOmniThread():
            self.push_change_archive_events(
                "pointingState", self._pointingState
            )

    def update_internal_pointingstate_callback(
        self, pointing_state: PointingState
    ) -> None:
        """Update internal pointingState attribute."""
        self._pointingState = pointing_state
        self.logger.debug("pointingState event will not be pushed")

    def kvalue_validation_callback(self) -> None:
        """Push an event for the kValueValidationResult attribute."""

        with tango.EnsureOmniThread():
            self.push_change_archive_events(
                "kValueValidationResult",
                str(int(self.component_manager.kValueValidationResult)),
            )
        self.logger.info(
            "k-value validation result: ResultCode.%s",
            ResultCode(self.component_manager.kValueValidationResult).name,
        )

    def update_kvalue_callback(self) -> None:
        """Push an event for the kValue attribute."""
        with tango.EnsureOmniThread():
            self.push_change_archive_events(
                "kValue",
                int(self.component_manager.kValue),
            )
        self.logger.info(
            "k-value : %s",
            self.component_manager.kValue,
        )

    # ------------------
    # Attributes methods
    # ------------------
    def read_dishMasterDevName(self) -> str:
        """Returns the dishMasterDevName attribute value."""
        return self.component_manager.dish_dev_name

    def write_dishMasterDevName(self, value: str) -> None:
        """Set the dishMasterDevName attribute."""
        self.component_manager.dish_dev_name = value

    def read_dishlnPointingDevName(self) -> str:
        """Returns the dishlnPointingDevName attribute value."""
        return self.component_manager.dish_pointing_dev_name

    def write_dishlnPointingDevName(self, value: str) -> None:
        """Set the dishlnPointingDevName attribute."""
        self.component_manager.dish_pointing_dev_name = value

    def read_trackTableErrors(self):
        """Read method for trackTableErrors"""
        return self.component_manager.errors_to_be_reported

    def read_isSubsystemAvailable(self) -> bool:
        """Read method for isSubsystemAvailable"""
        return self._isSubsystemAvailable

    def read_actualPointing(self) -> str:
        """Returns the actualPointing attribute value."""
        return json.dumps(self.component_manager.actual_pointing)

    def read_dishMode(self) -> DishMode:
        """
        Returns the dishMode attribute value.

        :return: The current value of the dishMode attribute.

        :rtype: DishMode

        """
        return self._dishMode

    def read_pointingState(self) -> PointingState:
        """
        Returns the pointingState attribute value.

        :return: The current value of the pointingState attribute.

        :rtype: PointingState

        """
        return self._pointingState

    @attribute(
        dtype="DevLong",
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
    )
    def kValue(self: MidTmcLeafNodeDish) -> int:
        """Returns the k-value attribute value."""
        return self.component_manager.kValue

    @attribute(
        dtype="str",
        access=AttrWriteType.READ,
    )
    def globalPointingModelParams(self: MidTmcLeafNodeDish) -> str:
        """Returns the globalpointingModelparam attribute value."""
        return json.dumps(self._global_pointing_model_params)

    @kValue.write
    def kValue(self: MidTmcLeafNodeDish, k_value: int) -> None:
        """Set the dish k-value."""
        self.component_manager.kValue = k_value

    @attribute(
        dtype="str",
        access=AttrWriteType.READ,
    )
    def kValueValidationResult(self: MidTmcLeafNodeDish) -> str:
        """Read method to get the k-value validation result"""
        return str(int(self.component_manager.kValueValidationResult))

    @attribute(
        dtype=ArgType.DevString,
        dformat=AttrDataFormat.SCALAR,
        access=AttrWriteType.READ_WRITE,
    )
    def sdpQueueConnectorFqdn(self: MidTmcLeafNodeDish) -> str:
        """
        This attribute is used for storing the FQDN of pointing_cal
        attribute from SDP queue connector device, which is required in
        calibration scan.
        :return: str
        """
        return self._sdpQueueConnectorFqdn

    @sdpQueueConnectorFqdn.write
    def sdpQueueConnectorFqdn(
        self: MidTmcLeafNodeDish, sdpqc_fqdn: str
    ) -> None:
        """
        This Method is used to get the SDP queue connector FQDN from
        subarray node and then Dish Leaf Node have to subscribe to its
        respective pointing_cal attribute on queue connector device.
        """

        self._sdpQueueConnectorFqdn = sdpqc_fqdn
        self.component_manager.process_sqpqc_attribute_fqdn(sdpqc_fqdn)
        self.push_change_archive_events(
            "sdpQueueConnectorFqdn", self._sdpQueueConnectorFqdn
        )

    @attribute(
        dtype=ArgType.DevDouble,
        dformat=AttrDataFormat.SPECTRUM,
        access=AttrWriteType.READ,
        max_dim_x=2,
    )
    def sourceOffset(self: MidTmcLeafNodeDish) -> list[float]:
        """
        This attribute is used for storing the commanded offsets
        received as a part of delta/partial configuration.
        This attribute is subscribed by SDP queue connector
        device.
        delta/partial configuration values like ca_offset_arcsec
        and ie_offset_arcsec are provided in the partial configuration
        json.
        source offset example:
        [cross_elevation_offset, elevation_offset]
        [0, .5]
        [.5, 0]
        [0, -.5], etc
        :return: list[float]
        """
        return self._sourceOffset

    @attribute(
        dtype=ArgType.DevString,
        dformat=AttrDataFormat.SCALAR,
        access=AttrWriteType.READ,
    )
    def lastPointingData(self: MidTmcLeafNodeDish):
        """
        This attribute is used to store the recent
        pointing data received in calibration scan
        :return: str
        """
        if self._last_pointing_data_attr_quality is AttrQuality.ATTR_VALID:
            return self._lastPointingData
        return (
            self._lastPointingData,
            TimeVal.totime(TimeVal.now()),
            self._last_pointing_data_attr_quality,
        )

    # --------
    # Commands
    # --------

    def is_SetStowMode_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def SetStowMode(
        self: MidTmcLeafNodeDish,
    ) -> Tuple[List[ResultCode], List[str]]:
        """Invokes SetStowMode command on DishMaster.

        :rtype: Tuple"""

        handler = self.get_command_object("SetStowMode")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    def is_SetStandbyLPMode_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def SetStandbyLPMode(self: MidTmcLeafNodeDish):
        """Invokes SetStandbyLPMode command on DishMaster (Standby-Low power)
        mode."""
        handler = self.get_command_object("SetStandbyLPMode")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    def is_SetOperateMode_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def SetOperateMode(
        self: MidTmcLeafNodeDish,
    ) -> Tuple[List[ResultCode], List[str]]:
        """Invokes SetOperateMode command on DishMaster device.

        :rtype: Tuple"""
        handler = self.get_command_object("SetOperateMode")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    def is_SetStandbyFPMode_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def SetStandbyFPMode(
        self: MidTmcLeafNodeDish,
    ) -> Tuple[List[ResultCode], List[str]]:
        """Invokes SetStandbyFPMode command on DishMaster (Standby-Full power)
        mode."""
        handler = self.get_command_object("SetStandbyFPMode")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    @command(
        dtype_in="DevString",
        doc_in="The scan_id in string",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    @DebugIt()
    def Scan(
        self: MidTmcLeafNodeDish, argin: str
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        Invokes Scan command on DishMaster

        :rtype: Tuple[List[ResultCode], List[str]]
        """
        handler = self.get_command_object("Scan")
        result_code, unique_id = handler(argin)
        return [result_code], [str(unique_id)]

    def is_Scan_allowed(
        self: MidTmcLeafNodeDish,
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether this command is allowed to be run in the current
        dish mode.

        :return: True if this command is allowed to be run in current
            dish mode, raises CommandNotAllowed in case is is not allowed and
            DeviceUnresponsive in case Device is not responsive.

        :rtype: Union[bool, CommandNotAllowed, DeviceUnresponsive]
        """
        return self.component_manager.is_scan_allowed()

    def is_EndScan_allowed(
        self: MidTmcLeafNodeDish,
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether this command is allowed to be run in the current
        dish mode.

        :return: True if this command is allowed to be run in current
            dish mode, raises CommandNotAllowed in case is is not allowed and
            DeviceUnresponsive in case Device is not responsive.

        :rtype: Union[bool, CommandNotAllowed, DeviceUnresponsive]
        """
        return self.component_manager.is_endscan_allowed()

    @command(
        dtype_in="DevVoid",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    @DebugIt()
    def EndScan(
        self: MidTmcLeafNodeDish,
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        Updates the scanID attribute of Dish Master to empty string

        :rtype: Tuple[List[ResultCode], List[str]]
        """
        handler = self.get_command_object("EndScan")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    def is_off_allowed(self: MidTmcLeafNodeDish):
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
    def Off(self: MidTmcLeafNodeDish) -> tuple:
        """
        Invokes On command on Dish Master.
        """
        handler = self.get_command_object("Off")
        result_code, unique_id = handler()
        return [result_code], [unique_id]

    def is_Configure_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def Configure(self: MidTmcLeafNodeDish, argin) -> tuple:
        """
        Invokes Configure command on Dish Master.
        """
        handler = self.get_command_object("Configure")
        result_code, unique_id = handler(argin)
        return [result_code], [unique_id]

    def is_StartCapture_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def StartCapture(self: MidTmcLeafNodeDish):
        """Triggers the DishMaster to start data capturing on the configured
        band."""

        return [
            [ResultCode.FAILED],
            ["StartCapture command will be refactored in later PI's"],
        ]

    def is_StopCapture_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def StopCapture(self: MidTmcLeafNodeDish):
        """Invokes StopCapture command on DishMaster on the set configured
        band."""

        return [
            [ResultCode.FAILED],
            ["StopCapture command will be refactored in later PI's"],
        ]

    def is_Track_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def Track(self: MidTmcLeafNodeDish, argin) -> tuple:
        """Invokes Track command on the DishMaster."""

        handler = self.get_command_object("Track")
        result_code, unique_id = handler(argin)
        return [result_code], [unique_id]

    def is_ConfigureBand_allowed(self: MidTmcLeafNodeDish) -> bool:
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
            device state.

        :rtype: boolean
        """
        self.logger.info("Checking if ConfigureBand is allowed")
        return self.component_manager.is_configureband_allowed()

    @command(
        dtype_in="str",
        doc_in="The input string contains dish receiver band.",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def ConfigureBand(self: MidTmcLeafNodeDish, argin) -> tuple:
        """Invokes ConfigureBand command on the DishMaster."""

        handler = self.get_command_object("ConfigureBand")
        result_code, unique_id = handler(argin)
        return [result_code], [unique_id]

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def TrackStop(
        self: MidTmcLeafNodeDish,
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        Invokes TrackStop command on DishMaster

        :rtype: tuple
        """
        handler = self.get_command_object("TrackStop")
        result_code, unique_id = handler()

        return [result_code], [str(unique_id)]

    def is_TrackStop_allowed(self: MidTmcLeafNodeDish) -> bool:
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
        doc_in="The JSON input string containing cross "
        + "elevation/elevation offsets.",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def TrackLoadStaticOff(
        self: MidTmcLeafNodeDish, argin: str
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        Invokes TrackLoadStaticOff command on DishMaster

        :rtype: tuple
        """
        handler = self.get_command_object("TrackLoadStaticOff")
        result_code, unique_id = handler(argin)

        return [result_code], [str(unique_id)]

    def is_TrackLoadStaticOff_allowed(self: MidTmcLeafNodeDish) -> bool:
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
            device state.

        :rtype: boolean
        """
        return self.component_manager.is_trackloadstaticoff_allowed()

    def is_Abort_allowed(self: MidTmcLeafNodeDish) -> bool:
        """
        Checks whether this command is allowed to be run in current
        device state

        :return: True if this command is allowed to be run in current device
            state

        :rtype: boolean
        """
        return self.component_manager.is_abort_allowed()

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Abort(self: MidTmcLeafNodeDish):
        """Invokes Abort command on the DishMaster."""

        handler = self.get_command_object("Abort")
        result_code, unique_id = handler()
        return [result_code], [unique_id]

    def is_Restart_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def Restart(self: MidTmcLeafNodeDish):
        """Invokes Restart command on the DishMaster."""

        return [
            [ResultCode.FAILED],
            ["Restart command will be refactored in later PI's"],
        ]

    def is_ObsReset_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def ObsReset(self: MidTmcLeafNodeDish):
        """Invokes ObsReset command on the MidTmcLeafNodeDish."""

        return [
            [ResultCode.FAILED],
            ["ObsReset command will be refactored in later PI's"],
        ]

    def is_SetKValue_allowed(self: MidTmcLeafNodeDish) -> bool:
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
    def SetKValue(
        self: MidTmcLeafNodeDish, k_value: int
    ) -> Tuple[List[ResultCode], List[str]]:
        """Invokes SetKValue command on the DishMaster."""
        handler = self.get_command_object("SetKValue")
        result_code, unique_id = handler(k_value)
        if result_code == ResultCode.OK:
            db = Database()
            value = {"kValue": {"__value": [self.component_manager.kValue]}}
            db.put_device_attribute_property(self._dishln_name, value)
            value = db.get_device_attribute_property(
                self._dishln_name, "kValue"
            )
            self.logger.info("k-value memorized successfully: %s", value)
            self.kvalue_validation_callback()
            self.update_kvalue_callback()
        return [result_code], [unique_id]

    @command(
        dtype_in="str",
        doc_in="The JSON input string containing Global " + "pointing data",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def ApplyPointingModel(
        self: MidTmcLeafNodeDish, argin: str
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        Invokes ApplyPointingModel command on DishMaster
        Its a dummy command at present.
        Will be renamed, once Dish ICD gets updated.

        :rtype: tuple
        """
        handler = self.get_command_object("ApplyPointingModel")
        result_code, unique_id = handler(argin)
        return [result_code], [str(unique_id)]

    def is_ApplyPointingModel_allowed(self: MidTmcLeafNodeDish) -> bool:
        """
        Checks whether this command is allowed to be run in the current
        device state.

        :return: True if this command is allowed to be run in current
            device state.

        :rtype: boolean
        """
        return self.component_manager.is_ApplyPointingModel_allowed()

    def create_component_manager(self: MidTmcLeafNodeDish):
        update_track_err_cb = self.update_track_table_errors_callback
        cm = DishLNComponentManager(
            dish_dev_name=self.MidDishControl,
            dishln_pointing_fqdn=self.MidPointingDevice,
            logger=self.logger,
            communication_state_callback=None,
            component_state_callback=None,
            pointing_callback=self.pointing_callback,
            kvalue_validation_callback=self.kvalue_validation_callback,
            _liveliness_probe=LivelinessProbeType.SINGLE_DEVICE,
            _event_receiver=True,
            _update_dishmode_callback=self.update_dishmode_callback,
            _update_dish_pointing_model_param=(
                self.update_global_pointing_param_callback
            ),
            _update_pointingstate_callback=(
                self.update_pointingstate_callback
            ),
            _update_internal_pointingstate_callback=(
                self.update_internal_pointingstate_callback
            ),
            event_subscription_check_period=self.EventSubscriptionCheckPeriod,
            liveliness_check_period=self.LivelinessCheckPeriod,
            dish_availability_check_timeout=self.DishAvailabilityCheckTimeout,
            adapter_timeout=self.AdapterTimeOut,
            command_timeout=self.CommandTimeOut,
            is_dish_abort_commands_enabled=self.IsDishAbortEnabled,
            _update_availablity_callback=self.update_availablity_callback,
            _update_source_offset_callback=self.update_source_offset_callback,
            _update_last_pointing_data_cb=self.update_last_pointing_data_cb,
            _update_track_table_errors_callback=update_track_err_cb,
            _update_health_state_callback=self.update_health_state_callback,
            max_track_table_retry=self.MaxTrackTableRetry,
            track_table_retry_duration=self.TrackTableRetryDuration,
        )
        return cm

    def init_command_objects(self: MidTmcLeafNodeDish) -> None:
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
            ("ConfigureBand", "configureband"),
            ("Track", "track"),
            ("TrackStop", "trackstop"),
            ("Off", "off"),
            ("SetKValue", "SetKValue"),
            ("TrackLoadStaticOff", "track_load_static_off"),
            ("Scan", "scan"),
            ("EndScan", "endscan"),
            ("ApplyPointingModel", "apply_pointing_model"),
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

        # as per base classes implementation, for SKABaseDevice
        # Abort is registered as AbortCommand
        self.register_command_object(
            "Abort",
            self.AbortCommand(
                self._command_tracker,
                self.component_manager,
                None,
                self.logger,
            ),
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
    Runs the MidTmcLeafNodeDish.

    :param args: Arguments internal to TANGO
    :param kwargs: Arguments internal to TANGO
    :return: MidTmcLeafNodeDish TANGO object.

    """
    return run((MidTmcLeafNodeDish,), args=args, **kwargs)


if __name__ == "__main__":
    main()
