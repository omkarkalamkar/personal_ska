"""
Configure class for DishLeafNode.
"""
from __future__ import annotations

import copy
import json
import logging
import threading
import time
from typing import Tuple

from ska_control_model import HealthState
from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import (
    DishMode,
    PointingState,
    TimeKeeper,
    TrackTableLoadMode,
)
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.configure_band_command import ConfigureBand
from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.commands.track_command import Track
from ska_tmc_dishleafnode.commands.track_load_static_off_command import (
    TrackLoadStaticOff,
)
from ska_tmc_dishleafnode.constants import ADJUST_TIMEOUT, RESET_OFFSETS
from ska_tmc_dishleafnode.enums import CORRECTION_KEY, CommandResult

configure_logging()
LOGGER = logging.getLogger(__name__)


class Configure(DishLNCommand):
    """
    A class for DishLeafNode's Configure command.

    Configures the Dish by setting pointing coordinates
    for a given scan.
    This function accepts the input json and calculate
    pointing parameters of Dish- Azimuth
    and Elevation Angle. Calculated parameters are again
    converted to json and fed to the
    dish master.

    """

    def __init__(
        self: Configure,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )

        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, logger
        )
        self.component_manager.configure_command_timer_list.append(
            self.timekeeper
        )

    # pylint: disable=unused-argument
    @timeout_tracker
    @error_propagation_tracker(
        "is_configure_completed",
        [True],
    )
    def invoke_configure(
        self: Configure,
        argin: str,
    ) -> Tuple[ResultCode, str]:
        """This is a long running method for Configure command, it
        executes do hook, invokes Configure command on Dish Master.

        :param argin: Input JSON string
        :type argin: str
        :return: : (ResultCode, str)
        :rtype: Tuple
        """
        self.component_manager.command_id = self.timeout_id
        self.component_manager.is_configure_command = True
        self.component_manager.command_in_progress = "Configure"
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        json_argument = json.loads(argin)

        array_layout = json_argument.get("layout_data")
        if array_layout is not None:
            self.component_manager.array_layout = array_layout
            self.logger.debug("Set array layout to: %s", array_layout)

        if json_argument.get("tmc") and json_argument["tmc"].get(
            "partial_configuration", False
        ):
            self.component_manager.partial_configure = True

        receiver_band = json_argument.get("dish", {}).get("receiver_band", "")
        if receiver_band:
            self.component_manager.receiver_band = receiver_band
            self.logger.debug(
                "Set receiver band to: %s",
                self.component_manager.receiver_band,
            )
        else:
            self.component_manager.receiver_band = (
                self.component_manager.dishConfiguredBand
            )

        result_code, message = self.do(argin)
        self.set_command_id(__class__.__name__)
        return result_code, message

    def update_primary_configuration(self, new_configuration: dict):
        """Update data provided in new configuration with primary
        configuration

        Args:
            new_configuration (dict): json argument in dict format
                for updating primary configuration.
        """
        pointing_data = new_configuration.get("pointing", {})
        # Update field
        if "field" in pointing_data:
            field = pointing_data["field"]
            self.component_manager.primary_configuration["pointing"][
                "field"
            ] = field
        # Update trajectory
        if "trajectory" in pointing_data:
            trajectory = pointing_data["trajectory"]
            self.component_manager.primary_configuration["pointing"][
                "trajectory"
            ] = trajectory
        # update projection
        if "projection" in pointing_data:
            projection = pointing_data["projection"]
            self.component_manager.primary_configuration["pointing"][
                "projection"
            ] = projection
        # Update wrap_sector key
        if "wrap_sector" in pointing_data:
            self.component_manager.primary_configuration["pointing"][
                "wrap_sector"
            ] = pointing_data["wrap_sector"]
        # Update receiver band
        dish_data = new_configuration.get("dish", {})
        if "receiver_band" in dish_data:
            new_receiver_band = dish_data["receiver_band"]
            self.component_manager.primary_configuration["dish"][
                "receiver_band"
            ] = new_receiver_band

    def update_task_status(self, **kwargs) -> None:
        """Method to update task status with result code and exception message
        if any.

        Args:
            kwargs: Keyword arguments. Specifically:

                - result
                - status
                - exception/message

        """
        try:
            result = kwargs.get("result")
            status = kwargs.get("status", TaskStatus.COMPLETED)
            message = kwargs.get("exception") or kwargs.get("message")
            self.logger.debug(
                "Command ID: %s | Updating task status with Result: %s",
                self.component_manager.command_id,
                kwargs,
            )
            if status == TaskStatus.ABORTED:
                self.task_callback(status=status)
                self.component_manager.command_in_progress = ""
                self.logger.info(
                    "Command ID: %s | "
                    + "Configure command execution aborted ",
                    self.component_manager.command_id,
                )
            elif result[0] == ResultCode.OK:
                self.component_manager.command_in_progress = ""
                self.task_callback(result=result, status=status)
                self.logger.info(
                    "Command ID: %s | "
                    + "Successfully executed Configure command on %s",
                    self.component_manager.command_id,
                    self.component_manager.dish_dev_name,
                )
            else:
                # Stop tracktable calculation if Configure command execution
                # is not completed successfully.
                self.logger.debug(
                    "Command ID: %s | Stopping trackTable calculation ",
                    self.component_manager.command_id,
                )
                self.dishln_pointing_device_adapter.StopProgramTrackTable()
                self.task_callback(
                    status=status,
                    result=result,
                    exception=message,
                )

                self.component_manager.command_in_progress = ""
            self.logger.debug(
                "Command ID: %s | Performing Configure command cleanup",
                self.component_manager.command_id,
            )
            self.component_manager.command_id = ""
            self.component_manager.receiver_band = ""
            self.component_manager.partial_configure = False
            self.component_manager.is_trackloadstatic_off = False
            self.component_manager.configure_band_lrcr = ResultCode.UNKNOWN
            self.component_manager.partial_configure_lrcr = ResultCode.UNKNOWN
            self.component_manager.configure_track_lrcr = ResultCode.UNKNOWN
            if (
                self.component_manager.correction_key
                == CORRECTION_KEY.RESET.value
            ):
                self.component_manager.correction_key = ""
            self.component_manager.clear_configure_command_events_flags()
            self.component_manager.command_unique_id_dict.clear()
            self.logger.debug("Configure command cleanup completed.")

        except Exception as e:
            self.logger.exception(
                "Command ID: %s | Failed to update "
                + "task status ,Exception: %s",
                self.component_manager.command_id,
                str(e),
            )

    # pylint: enable=unused-argument
    def validate_json_argument(
        self: Configure, input_argin: dict
    ) -> Tuple[ResultCode, str]:
        """Validates the json argument

        Args:
            input_argin (dict): input json to be validated.

        Returns:
            Tuple[ResultCode, str]: Resultcode and message.

        """

        if "pointing" not in input_argin:
            return (
                ResultCode.REJECTED,
                "pointing key is not present in the configure input json.",
            )

        if "tmc" in input_argin and input_argin["tmc"].get(
            "partial_configuration"
        ):
            if "target" not in input_argin["pointing"]:
                return (
                    ResultCode.REJECTED,
                    "target key is not present in the input json argument.",
                )
        else:
            if "dish" not in input_argin:
                return (
                    ResultCode.REJECTED,
                    "dish key is not present in the input json argument.",
                )

            if "receiver_band" not in input_argin["dish"]:
                return (
                    ResultCode.REJECTED,
                    "receiverBand key is not present in the input json "
                    + "argument.",
                )

        return (ResultCode.OK, "")

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self: Configure, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke Configure command on dish.

        Args:
            argin (str): A String in a JSON format
                that includes pointing parameters
                of Dish- Azimuth and Elevation Angle.

        .. literalinclude:: ../../../../tests/data/dishleafnode_configure.json
            :language: json
            :caption: Example JSON for Configure

        Note:
            Enter input json without spaces.

        Returns:
            Tuple[ResultCode, str]: Resultcode and message

        Raises:
            DevFailed: If error occurs while invoking ConfigureBand<> command
                on DishMaster or
                if the json string contains invalid data.

        """
        try:
            result_code, message = self.init_adapter()
            if result_code == ResultCode.FAILED:
                self.logger.error(
                    "Command ID: %s | Failed to find adapter for device: %s",
                    self.component_manager.command_id,
                    self.component_manager.dish_dev_name,
                )
                return result_code, message

            if not self.component_manager.partial_configure:
                self.component_manager.trackTableLoadMode = (
                    TrackTableLoadMode.NEW
                )
                self.component_manager.is_tracktable_provided.clear()

            json_argument = json.loads(argin)
            if not self.component_manager.partial_configure:
                self.component_manager.primary_configuration = json_argument
                json_argument = self.component_manager.primary_configuration
            else:
                self.update_primary_configuration(json_argument)
                json_argument = self.component_manager.primary_configuration

            self.logger.info("Primary config is %s", json_argument)
            reset_offset = (
                self.component_manager.correction_key
                == CORRECTION_KEY.RESET.value
            )
            collimation_offsets = self.get_ie_ca_offsets_if_provided(
                json.loads(argin), reset_offset
            )
            # Invoke track load static off when collimation offsets
            # provided and correction key is provided as RESET
            if collimation_offsets:
                self.component_manager.is_trackloadstatic_off = True
                self.invoke_trackloadstaticoff(
                    json_argument, collimation_offsets
                )

            try:
                pointing_device_conf_json = copy.deepcopy(json_argument)
                # Minimal change: include array_layout if available
                array_layout = getattr(
                    self.component_manager, "array_layout", None
                )
                target_payload = {
                    "pointing": pointing_device_conf_json["pointing"],
                    "tmc": pointing_device_conf_json.get("tmc", {}),
                }
                if array_layout is not None:
                    target_payload["array_layout"] = array_layout
                target_data = json.dumps(target_payload)

                self.logger.debug(
                    "Main/Delta Config:"
                    " Calling "
                    "GenerateProgramTrackTable()"
                )
                result_code, _ = self.invoke_generate_program_track_table(
                    target_data
                )
            except Exception as exception:
                self.logger.exception(
                    "Command ID: %s | Failed to generate "
                    + "program track table for %s , Exception: %s",
                    self.component_manager.command_id,
                    self.component_manager.dish_dev_name,
                    str(exception),
                )
                self.component_manager.current_track_table_error = (
                    f"Exception while generating programTrackTable "
                    f"{exception}"
                )
                if self.component_manager._update_health_state_callback:
                    self.component_manager._update_health_state_callback(
                        HealthState.DEGRADED
                    )
                return (
                    ResultCode.FAILED,
                    (
                        "There was an error while starting the generation of "
                        + "program track table: %s",
                        exception,
                    ),
                )
            if not reset_offset and not collimation_offsets:
                return self.invoke_configure_band_on_dish(json_argument)

        except Exception as exception:
            self.logger.exception(
                "Command ID: %s | Failed to invoke Configure command on %s"
                + "Exception: %s",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
                str(exception),
            )

            return (
                ResultCode.FAILED,
                "The invocation of the Configure command is failed on"
                + f" Dish Master Device {self.dish_master_adapter.dev_name}."
                + "Reason: Error in calling the Configure command on"
                + f" Dish Master: {exception}",
            )
        return ResultCode.QUEUED, ""

    def invoke_generate_program_track_table(
        self, target_data: str
    ) -> Tuple[ResultCode, str]:
        """Invoke Generate program track table on
        dish pointing device

        Args:
            target_data (str): targetData

        Returns:
            Tuple[ResultCode, str]: Tuple of ResultCode and message.

        """
        self.dishln_pointing_device_adapter.targetData = target_data
        (
            result_code,
            msg,
        ) = self.dishln_pointing_device_adapter.GenerateProgramTrackTable()
        if self.component_manager._update_health_state_callback:
            self.component_manager._update_health_state_callback(
                HealthState.OK
            )
        return result_code, msg

    def invoke_configure_band_on_dish(
        self, json_argument
    ) -> Tuple[ResultCode, str]:
        """Invoke Configure band on Dish

        Args:
            json_argument (dict): Input json

        Returns:
            Tuple[ResultCode, str]: Tuple of ResultCode and message.

        """
        receiver_band = json_argument.get("dish", {}).get("receiver_band", "")
        self.logger.info("Receiver band is %s", receiver_band)

        def _invoke_configure_band_callback(
            status=None,
            progress=None,
            result=None,
            exception=None,
        ):
            """
            Method for invoking ConfigureBand callback
            """
            self.logger.debug(
                "Command ID: %s | "
                + "Received result for ConfigureBand command"
                + " Result: %s , Progress: %s ,Exception: %s",
                self.component_manager.command_id,
                result,
                progress,
                str(exception),
            )
            if result is None:
                pass
            else:
                result_code, message = result
                self.component_manager.set_configure_band_result_dict(
                    result_code, message, exception, status
                )
                self.component_manager.configure_band_lrcr = result_code
                if self.component_manager.abort_event.is_set():
                    return
                if result_code == ResultCode.OK:
                    self.start_dish_tracking(json_argument)
                elif result_code == ResultCode.FAILED:
                    self.logger.info(
                        "Command ID: %s | "
                        + "ResultCode: %s for configure band command",
                        self.component_manager.command_id,
                        str(result_code),
                    )
                    # If timed out has occurred for configure band then update
                    # exception message for configure command
                    if "Timeout has occurred" in exception:
                        exception_message = (
                            "Timeout occurred while waiting for "
                            "configuredBand command to be completed in "
                            "Configure command."
                        )
                        self.logger.exception(exception_message)
                        self.set_failure_for_configure(exception_message)
                    else:
                        self.component_manager.observable.notify_observers(
                            command_exception=True
                        )

        if receiver_band != self.component_manager.dishConfiguredBand:
            configure_band_command = ConfigureBand(
                self.component_manager,
                self.op_state_model,
                self._adapter_factory,
                logger=self.logger,
                is_configure_command=True,
            )
            configure_band_command.configure_band(
                argin=json.dumps(json_argument),
                logger=self.logger,
                task_callback=_invoke_configure_band_callback,
                task_abort_event=self.component_manager.abort_event,
            )

            if (
                self.component_manager.get_configure_band_result_code()
                == ResultCode.FAILED
            ):
                return (
                    self.component_manager.get_configure_band_result_code(),
                    self.component_manager.get_configure_band_result_dict()[
                        "exception"
                    ],
                )
        elif (
            receiver_band == self.component_manager.dishConfiguredBand
            and self.component_manager.dishMode == DishMode.OPERATE
        ):
            self.component_manager.configure_band_lrcr = ResultCode.OK
            self.start_dish_tracking(json_argument)
        else:
            self.component_manager.configure_band_lrcr = ResultCode.OK
            self.start_dish_tracking(json_argument)

        return ResultCode.QUEUED, ""

    def get_ie_ca_offsets_if_provided(
        self, config_json: dict, reset_offset: bool
    ) -> list:
        """This check if ca_offset_arcsec or ie_offset_arcsec provided
        in config json and return offsets

        :param config_json: Configuration json
        :type config_json: dict
        :param reset_offset: Bool value
        :type reset_offset: bool
        :return: Offset list
        """
        if reset_offset:
            return RESET_OFFSETS
        offsets = []
        pointing_data = config_json.get("pointing", {})
        if pointing_data:
            target_data = pointing_data.get("target", {})
            if (
                "ca_offset_arcsec" in target_data
                or "ie_offset_arcsec" in target_data
            ):
                offsets.append(target_data.get("ca_offset_arcsec", 0.0))
                offsets.append(target_data.get("ie_offset_arcsec", 0.0))
            elif (
                "ca_offset_arcsec" in pointing_data
                or "ie_offset_arcsec" in pointing_data
            ):
                offsets.append(pointing_data.get("ca_offset_arcsec", 0.0))
                offsets.append(pointing_data.get("ie_offset_arcsec", 0.0))
        return offsets

    def invoke_trackloadstaticoff(
        self: Configure,
        input_json: dict,
        collimation_offsets: list,
    ) -> Tuple[ResultCode, str]:
        """Extracts the offsets from input json and invokes the
        TrackLoadStaticOff command on DishMaster device.

        :param input_json: Input json for Configure command
        :type input_json: dict

        :returns: Tuple[ResultCode, str]
        """
        offsets_argin = collimation_offsets

        # pylint: disable=unused-argument
        def _invoke_trackstaticloadoff_callback(
            status=None,
            progress=None,
            result=None,
            exception=None,
        ):
            """
            Method for invoking TrackStaticLoadOff callback
            """
            if result is None:
                pass
            else:
                result_code, message = result
                self.component_manager.set_track_load_static_off_result_dict(
                    result_code, message, exception, status
                )
                self.component_manager.partial_configure_lrcr = result_code
                self.logger.info(
                    "Command ID: %s | "
                    "Result code for Track load: %s  "
                    ",Correction Key: %s ,"
                    "Partial Configure: %s",
                    self.component_manager.command_id,
                    str(result_code),
                    self.component_manager.correction_key,
                    self.component_manager.partial_configure,
                )
                if self.component_manager.abort_event.is_set():
                    return
                if result_code == ResultCode.OK:
                    self.invoke_configure_band_on_dish(input_json)
                elif result_code == ResultCode.FAILED:
                    # If timed out has occurred for trackload
                    # static off then update
                    # exception message for configure command
                    if "Timeout has occurred" in exception:
                        exception_message = (
                            "Timeout occurred while waiting for "
                            "TrackStaticLoadOff command"
                            " to be completed in Configure command."
                        )
                        self.set_failure_for_configure(exception_message)
                        self.logger.exception(exception_message)
                    else:
                        self.component_manager.observable.notify_observers(
                            command_exception=True
                        )
                self.component_manager.command_in_progress = "Configure"

        # pylint: enable=unused-argument
        # Call the TrackStaticLoadOff command
        track_load_static_off_command = TrackLoadStaticOff(
            self.component_manager,
            self.op_state_model,
            self._adapter_factory,
            self.logger,
            is_configure_command=True,
        )
        # pylint: disable=E1123
        track_load_static_off_command.invoke_track_load_static_off(
            argin=json.dumps(offsets_argin),
            logger=self.logger,
            task_callback=_invoke_trackstaticloadoff_callback,
            task_abort_event=self.component_manager.abort_event,
        )
        if (
            self.component_manager.get_track_load_static_off_result_code()
            == ResultCode.FAILED
        ):
            return (
                self.component_manager.get_track_load_static_off_result_code(),
                self.component_manager.get_track_load_static_off_result_dict()[
                    "exception"
                ],
            )
        self.component_manager.update_source_offset_callback(offsets_argin)
        return ResultCode.QUEUED, ""

    def start_dish_tracking(self: Configure, json_argument: dict):
        """
        Invoke Track after waiting for DishMode to Operate

        Args:
            json_argument (dict): json argument.

        """
        # Only invoke Track if dish is in OPERATE mode
        if self.component_manager.dishMode == DishMode.OPERATE:
            self.logger.info(
                "Command ID: %s | Dish is already in DishMode OPERATE on %s.",
                self.component_manager.command_id,
                self.component_manager.track_result,
            )
            self.invoke_track_command(json_argument)
        else:
            self.ensure_dish_in_right_dish_mode(json_argument)

    def ensure_dish_in_right_dish_mode(self: Configure, _json_argument: dict):
        """This method set dish to Operate Mode

        Args:
            json_argument (dict): json argument for invoking track_command.
        """
        self.logger.debug(
            (
                "Command ID: %s | Dish is not in OPERATE mode, "
                "cannot invoke Track command on %s."
            ),
            self.component_manager.command_id,
            self.component_manager.dish_dev_name,
        )

    def invoke_track_command(self: Configure, json_argument: dict):
        """Invoke Track command on dish

        Args:
            json_argument (dict): json argument.

        """

        if self.component_manager.pointingState in [
            PointingState.TRACK,
            PointingState.SLEW,
        ]:
            self.logger.debug(
                "Command ID: %s | Dish is already tracking/slewing. "
                + "Track() command is not invoked on %s",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
            )
            message = "Dish is already tracking/slewing."
            self.component_manager.set_track_result_dict(
                ResultCode.OK, message
            )
            self.logger.debug(
                "Command ID: %s | Track command Result: %s",
                self.component_manager.command_id,
                self.component_manager.track_result,
            )
            self.component_manager.configure_track_lrcr = ResultCode.OK
            self.component_manager.observable.notify_observers(
                attribute_value_change=True
            )
        else:
            track_table_provided_thread = threading.Thread(
                target=self.is_tracktable_provided, args=(json_argument,)
            )
            track_table_provided_thread.start()

    def invoke_track_command_on_dish(self, json_argument: dict):
        """Invoke Track command on dish

        Args:
            json_argument (dict): json argument for invoking track command.

        """

        def _invoke_track_callback(
            status=None,
            progress=None,
            result=None,
            exception=None,
        ):
            """
            Method for invoking Track callback
            """
            if result is None:
                pass
            else:
                self.logger.info(
                    "Command ID: %s | Track Command Result: %s "
                    + "and Progress: %s",
                    self.component_manager.command_id,
                    str(result),
                    progress,
                )
                result_code, message = result
                self.component_manager.set_track_result_dict(
                    result_code, message, exception, status
                )
                if result_code == ResultCode.OK:
                    # Invoke Track command
                    self.component_manager.configure_track_lrcr = ResultCode.OK
                    self.component_manager.observable.notify_observers(
                        attribute_value_change=True
                    )
                elif result_code == ResultCode.FAILED:
                    # If timed out has occurred for track
                    # then update exception message for
                    # configure command
                    if "Timeout has occurred" in exception:
                        exception_message = (
                            "Timeout occurred while waiting for "
                            "Track command to"
                            " be completed in Configure command."
                        )
                        self.set_failure_for_configure(exception_message)
                        self.logger.exception(exception_message)
                    else:
                        self.component_manager.observable.notify_observers(
                            command_exception=True
                        )

        # pylint: enable=unused-argument
        track_command = Track(
            self.component_manager,
            self.op_state_model,
            self._adapter_factory,
            logger=self.logger,
            is_configure_command=True,
        )
        track_command.track(
            argin=json_argument,
            logger=self.logger,
            task_callback=_invoke_track_callback,
            task_abort_event=self.component_manager.abort_event,
        )

        if self.component_manager.get_track_result_code() == ResultCode.FAILED:
            self.component_manager.observable.notify_observers(
                command_exception=True
            )

    def is_tracktable_provided(self, json_argument: str) -> CommandResult:
        """
        Returns enum ACHIEVED if programTrackTable is provided to dish.

        Args:
            json_argument (str): json argument.

        Returns:
            CommandResult: Enum ACHIEVED if programTrackTable
            is provided to dish, NOT_ACHIEVED if it is not provided
            and ABORTED if Abort() is called while configuring dish.

        """
        track_table_status = CommandResult.NOT_ACHIEVED

        start_time = time.time()
        elapsed_time = 0
        while (
            elapsed_time
            < self.component_manager.command_timeout - ADJUST_TIMEOUT
        ):
            if self.component_manager.abort_event.is_set():
                self.logger.debug(
                    "Command ID: %s | "
                    + "Abort() command is invoked while configuring dish.",
                    self.component_manager.command_id,
                )
                track_table_status = CommandResult.ABORTED
                break

            if self.component_manager.is_tracktable_provided.is_set():
                track_table_status = CommandResult.ACHIEVED
                self.invoke_track_command_on_dish(json_argument)
                break
            time.sleep(0.1)
            elapsed_time = time.time() - start_time

        self.logger.debug(
            "Command ID: %s | "
            + "Exited the loop that waits to supply the tracktable before"
            + " invoking the Track command.",
            self.component_manager.command_id,
        )
        if not self.component_manager.is_tracktable_provided.is_set():
            # Set Failure for configure
            self.logger.debug(
                "Command ID: %s | Timed out occurred for track table",
                self.component_manager.command_id,
            )
            self.set_failure_for_configure(
                "Dish manager did not receive TrackTable. "
                "Track() command is not invoked on the Dish."
            )
        return track_table_status

    def set_failure_for_configure(self, message: str):
        """Set failure for configure

        Args:
            message (str): Exception message

        """
        # pylint: disable=no-member
        if hasattr(self, "ct"):
            self.component_manager.long_running_result_callback(
                self.ct.command_id,
                ResultCode.FAILED,
                exception_msg=message,
            )
            self.component_manager.observable.notify_observers(
                command_exception=True
            )
