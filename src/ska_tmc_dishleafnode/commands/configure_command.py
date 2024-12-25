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
from ska_tmc_common import DishMode, PointingState, TimeKeeper
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.configure_band_command import ConfigureBand
from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.commands.setoperatemode import SetOperateMode
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
        if json_argument.get("tmc"):
            self.component_manager.partial_configure = True

        if not self.component_manager.partial_configure:
            self.component_manager.receiver_band = json_argument["dish"][
                "receiver_band"
            ]

        result_code, message = self.do(argin)
        self.set_command_id(__class__.__name__)
        return result_code, message

    def update_task_status(self, **kwargs) -> None:
        """Method to update task status with result code and exception message
        if any."""
        try:
            result = kwargs.get("result")
            status = kwargs.get("status", TaskStatus.COMPLETED)
            message = kwargs.get("exception") or kwargs.get("message")
            self.logger.info(
                "result: %s status: %s message: %s", result, status, message
            )

            if status == TaskStatus.ABORTED:
                self.task_callback(status=status)
                self.component_manager.command_in_progress = ""
                self.logger.info("Configure command execution is aborted.")
            elif result[0] == ResultCode.OK:
                self.component_manager.command_in_progress = ""
                self.task_callback(result=result, status=status)
                self.logger.info(
                    "Executed the Configure command successfully on %s",
                    self.dish_master_adapter.dev_name,
                )
            else:
                self.task_callback(
                    status=status,
                    result=result,
                    exception=message,
                )

                self.component_manager.command_in_progress = ""
            self.component_manager.command_id = ""
            self.component_manager.receiver_band = ""
            self.component_manager.partial_configure = False
            self.component_manager.configure_band_lrcr = ResultCode.UNKNOWN
            self.component_manager.configure_setoperate_mode = (
                ResultCode.UNKNOWN
            )
            self.component_manager.partial_configure_lrcr = ResultCode.UNKNOWN
            self.component_manager.configure_track_lrcr = ResultCode.UNKNOWN
            if (
                self.component_manager.correction_key
                == CORRECTION_KEY.RESET.value
            ):
                self.component_manager.correction_key = ""
            self.component_manager.clear_configure_command_events_flags()
            self.logger.info("Configure command cleanup completed.")

        except Exception as e:
            self.logger.exception(
                "Exception occurred while updating task status %s", e
            )

    # pylint: enable=unused-argument
    def validate_json_argument(
        self: Configure, input_argin: dict
    ) -> Tuple[ResultCode, str]:
        """Validates the json argument

        :return: Resulcode and message
        :rtype: tuple
        """

        if "pointing" not in input_argin:
            return (
                ResultCode.FAILED,
                "pointing key is not present in the configure input json.",
            )

        if "tmc" in input_argin:
            if (
                "tmc" in input_argin
                and "target" not in input_argin["pointing"]
            ):
                return (
                    ResultCode.FAILED,
                    "target key is not present in the input json argument.",
                )
        else:
            if "dish" not in input_argin:
                return (
                    ResultCode.FAILED,
                    "dish key is not present in the input json argument.",
                )

            if "receiver_band" not in input_argin["dish"]:
                return (
                    ResultCode.FAILED,
                    "receiverBand key is not present in the input json "
                    + "argument.",
                )

        return (ResultCode.OK, "")

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self: Configure, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke Configure command on dish.

        :param argin:
            A String in a JSON format that includes pointing parameters
            of Dish- Azimuth and
            Elevation Angle.

                Example:
                {"pointing":{"target":{"refrence_frame":"ICRS",
                "target_name":"Polaris Australis",
                "ra":"21:08:47.92",
                "dec":"-88:57:22.9"}},
                "dish":{"receiver_band":"1"}}

        :return: Resulcode and message
        :rtype: tuple

        raises:
            DevFailed If error occurs while invoking ConfigureBand<> command
            on DishMaster or
            if the json string contains invalid data.

        """
        try:
            result_code, message = self.init_adapter()
            if result_code == ResultCode.FAILED:
                self.logger.error(
                    "Adapter for device : %s is not found ",
                    self.component_manager.dish_dev_name,
                )
                return result_code, message

            json_argument = json.loads(argin)

            reset_offset = (
                self.component_manager.correction_key
                == CORRECTION_KEY.RESET.value
            )
            if reset_offset and "tmc" not in json_argument:
                result_code, message = self.invoke_trackloadstaticoff(
                    json_argument, reset_offset=True
                )
                self.component_manager.command_in_progress = "Configure"
                if result_code in [
                    ResultCode.FAILED,
                    ResultCode.REJECTED,
                    ResultCode.NOT_ALLOWED,
                ]:
                    return result_code, message

            if json_argument.get("tmc"):
                return self.invoke_trackloadstaticoff(
                    json_argument, reset_offset=reset_offset
                )

            try:
                pointing_device_conf_json = copy.deepcopy(json_argument)
                if "correction" in pointing_device_conf_json["pointing"]:
                    pointing_device_conf_json["pointing"].pop("correction")

                self.dishln_pointing_device_adapter.targetData = json.dumps(
                    {"pointing": pointing_device_conf_json["pointing"]}
                )
                self.dishln_pointing_device_adapter.GenerateProgramTrackTable()
                if self.component_manager._update_health_state_callback:
                    self.component_manager._update_health_state_callback(
                        HealthState.OK
                    )
            except Exception as exception:
                self.logger.exception(
                    "Unable to generate programTrackTable: %s",
                    exception,
                )
                self.component_manager.current_track_table_error = (
                    f"Exception while generating programTrackTable {exception}"
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
            if not reset_offset:
                self.logger.info("Invoking ConfigureBand command")
                return self.invoke_configure_band_on_dish(json_argument)

        except Exception as exception:
            self.logger.exception(
                f"Command invocation failed with exception: {exception}"
            )
            return (
                ResultCode.FAILED,
                "The invocation of the Configure command is failed on"
                + f" Dish Master Device {self.dish_master_adapter.dev_name}."
                + "Reason: Error in calling the Configure command on"
                + f" Dish Master: {exception}",
            )
        return ResultCode.QUEUED, ""

    def invoke_configure_band_on_dish(self, json_argument):
        """Invoke Configure band on Dish
        :param json_argument: Input json
        :type json_argument: dict
        """

        def _invoke_configure_band_callback(
            status=None,
            progress=None,
            result=None,
            exception=None,
        ):
            """
            Method for invoking ConfigureBand callback
            """
            # once configure band completed then invoke set operate mode
            # command
            self.logger.debug(
                "Received result for configure band %s and %s and %s",
                result,
                progress,
                exception,
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
                    # Invoke set operate mode command
                    self.invoke_setopermode_command(json_argument)
                elif result_code == ResultCode.FAILED:
                    self.logger.info(
                        "Result code is %s for configure band command",
                        result_code,
                    )
                    # If timed out has occurred for configure band then update
                    # exception message for configure command
                    if "Timeout has occurred" in exception:
                        exception_message = (
                            "Timeout occurred while waiting for "
                            "configuredBand command to be completed in "
                            "Configure command."
                        )
                        self.set_failure_for_configure(exception_message)
                    else:
                        self.component_manager.observable.notify_observers(
                            command_exception=True
                        )

        # pylint: enable=unused-argument
        configure_band_command = ConfigureBand(
            self.component_manager,
            self.op_state_model,
            self._adapter_factory,
            logger=self.logger,
            is_configure_command=True,
        )
        configure_band_command.configure_band(
            argin=self.component_manager.receiver_band,
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
        return ResultCode.QUEUED, ""

    def invoke_setopermode_command(self, json_argument: dict):
        """Invoke Set Operate mode command"""
        if self.component_manager.dishMode != DishMode.STOW:
            self.start_dish_tracking(json_argument)

    def invoke_trackloadstaticoff(
        self: Configure,
        input_json: dict,
        reset_offset: bool = False,
    ) -> Tuple[ResultCode, str]:
        """Extracts the offsets from input json and invokes the
        TrackLoadStaticOff command on DishMaster device.

        :param input_json: Input json for Configure command
        :type input_json: dict

        :returns: Tuple[ResultCode, str]
        """
        offsets_argin = []

        # Extracting and setting cross elevation offset. Considering
        # 0.0 if the key is omitted

        if reset_offset:
            offsets_argin = RESET_OFFSETS
            self.logger.debug(
                "Pointing offsets have been reset to [0.0, 0.0] "
                "and correction key set to %s",
                CORRECTION_KEY.RESET.value,
            )
        else:
            offsets_argin.append(
                input_json["pointing"]["target"].get("ca_offset_arcsec") or 0.0
            )

            # Extracting and setting elevation offset. Considering 0.0 if
            # the key is omitted
            offsets_argin.append(
                input_json["pointing"]["target"].get("ie_offset_arcsec") or 0.0
            )

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
                    "Result code for track load %s and %s and %s",
                    result_code,
                    self.component_manager.correction_key,
                    self.component_manager.partial_configure,
                )
                if self.component_manager.abort_event.is_set():
                    return
                if result_code == ResultCode.OK:
                    if (
                        self.component_manager.correction_key
                        == CORRECTION_KEY.RESET.value
                        and not self.component_manager.partial_configure
                    ):
                        self.invoke_configure_band_on_dish(input_json)
                    else:
                        self.component_manager.observable.notify_observers(
                            attribute_value_change=True
                        )
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
        # pylint: enable=E1123
        self.component_manager.update_source_offset_callback(offsets_argin)
        return ResultCode.QUEUED, ""

    def start_dish_tracking(self: Configure, json_argument):
        """
        Invoke Track after waiting for DishMode to Operate

        Args: None

        return: None"""
        if self.component_manager.dishMode != DishMode.OPERATE:
            self.ensure_dish_in_right_dish_mode(json_argument)
        else:
            message = "Dish is already in DishMode OPERATE."
            self.component_manager.update_set_operate_mode_result_dict(
                ResultCode.OK, message
            )
            self.component_manager.configure_setoperate_mode_lrcr = (
                ResultCode.OK
            )
            self.logger.debug(
                "set_operate_mode_result result: %s",
                self.component_manager.set_operate_mode_result,
            )
            self.invoke_track_command(json_argument)

    def ensure_dish_in_right_dish_mode(self: Configure, json_argument: dict):
        """This method set dish to Operate Mode

        return: None
        """
        self.logger.info("Invoking SetOperateMode command")

        # pylint: disable=unused-argument
        def _invoke_setoperatemode_callback(
            status=None,
            progress=None,
            result=None,
            exception=None,
        ):
            """
            Method for invoking setoperatemode callback
            """
            self.logger.info("Received Setoperate mode result %s", result)
            if result is None:
                pass
            else:
                result_code, message = result
                self.component_manager.update_set_operate_mode_result_dict(
                    result_code, message, exception, status
                )
                self.component_manager.configure_setoperate_mode_lrcr = (
                    result_code
                )
                if self.component_manager.abort_event.is_set():
                    return
                if result_code == ResultCode.OK:
                    # Invoke Track command
                    self.invoke_track_command(json_argument)
                elif result_code == ResultCode.FAILED:
                    # If timed out has occurred for trackload
                    # static off then update
                    # exception message for configure command
                    if "Timeout has occurred" in exception:
                        exception_message = (
                            "Timeout occurred while waiting for "
                            "SetOperateMode command to"
                            " be completed in Configure command."
                        )
                        self.set_failure_for_configure(exception_message)
                    else:
                        self.component_manager.observable.notify_observers(
                            command_exception=True
                        )

        # pylint: enable=unused-argument
        setoperatemode_command = SetOperateMode(
            self.component_manager,
            self.op_state_model,
            self._adapter_factory,
            logger=self.logger,
            is_configure_command=True,
        )
        setoperatemode_command.set_operate_mode(
            logger=self.logger,
            task_callback=_invoke_setoperatemode_callback,
            task_abort_event=self.component_manager.abort_event,
        )

        if (
            self.component_manager.get_set_operate_mode_result_code()
            == ResultCode.FAILED
        ):
            self.component_manager.observable.notify_observers(
                command_exception=True
            )

    def invoke_track_command(self: Configure, json_argument):
        """Invoke Track command on dish

        :return: None
        """

        if self.component_manager.pointingState in [
            PointingState.TRACK,
            PointingState.SLEW,
        ]:
            self.logger.info(
                "Dish is already tracking/slewing. Track() command "
                + "is not invoked."
            )
            message = "Dish is already tracking/slewing."
            self.component_manager.set_track_result_dict(
                ResultCode.OK, message
            )
            self.logger.debug(
                "Track result: %s",
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

    def invoke_track_command_on_dish(self, json_argument):
        """Invoke Track command on dish"""

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
                self.logger.info("Track result: %s and %s", result, progress)
                result_code, message = result
                self.component_manager.set_track_result_dict(
                    result_code, message, exception, status
                )
                self.component_manager.configure_track_lrcr = ResultCode.OK
                self.component_manager.observable.notify_observers(
                    attribute_value_change=True
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

    def is_tracktable_provided(self, json_argument):
        """
        Returns enum ACHIEVED if programTrackTable is provided to dish.
        """
        track_table_status = CommandResult.NOT_ACHIEVED

        start_time = time.time()
        elapsed_time = 0
        track_table = []
        while (
            elapsed_time
            < self.component_manager.command_timeout - ADJUST_TIMEOUT
        ):
            if self.component_manager.abort_event.is_set():
                self.logger.info(
                    "AbortCommands() command is invoked while"
                    + " configuring dish."
                )
                track_table_status = CommandResult.ABORTED
                break
            track_table = self.dish_master_adapter.programTrackTable
            self.logger.debug("is_tracktable_provided: %s", track_table)

            if len(track_table) > 0:
                track_table_status = CommandResult.ACHIEVED
                self.invoke_track_command_on_dish(json_argument)
                break
            time.sleep(0.5)
            elapsed_time = time.time() - start_time
        self.logger.info("Come out of loop")
        if len(track_table) == 0:
            # Set Failure for configure
            self.logger.info("Timed out occurred for track table")
            self.set_failure_for_configure(
                "Dish manager did not receive TrackTable. "
                "Track() command is not invoked on the Dish."
            )
        return track_table_status

    def set_failure_for_configure(self, message):
        """Set failure for configure"""
        # pylint: disable=no-member
        self.component_manager.long_running_result_callback(
            self.ct.command_id,
            ResultCode.FAILED,
            exception_msg=message,
        )
        self.component_manager.observable.notify_observers(
            command_exception=True
        )
