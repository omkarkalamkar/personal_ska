"""
Configure class for DishLeafNode.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from logging import Logger
from typing import Callable, List, Optional, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import DishMode, PointingState, TimeoutCallback

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import (
    COMMAND_COMPLETION_MESSAGE,
    RESET_OFFSETS,
)
from ska_tmc_dishleafnode.enums import CORRECTION_KEY

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

        self.track_table_process = None
        self.timeout_id = None
        self.timeout_callback = None
        self.task_callback: Callable
        self.partial_configure = False
        self.reset_configure_command_result_values()

    # pylint: disable=unused-argument
    def invoke_configure(
        self: Configure,
        argin: str,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """This is a long running method for Configure command, it
        executes do hook, invokes Configure command on Dish Master.

        :param argin: Input JSON string
        :type argin: str
        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        :return: : None
        :rtype: None
        """
        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback = TimeoutCallback(self.timeout_id, self.logger)

        self.component_manager.abort_event = task_abort_event
        # Indicate that the task has started
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        self.set_command_id(__class__.__name__)
        self.component_manager.command_in_progress = "Configure"
        self.component_manager.start_timer(
            self.timeout_id,
            self.component_manager.command_timeout,
            self.timeout_callback,
        )
        return_code, message = self.do(argin)
        lrcr_callback = self.component_manager.long_running_result_callback
        if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            logger.info(
                "Setting taskcallback to FAILED with message: %s",
                message,
            )
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(return_code, message),
                exception=message,
            )
            self.component_manager.command_in_progress = ""
        else:
            if (
                self.component_manager.command_in_progress
                not in self.component_manager.supported_commands
            ):
                self.component_manager.command_in_progress = ""
            if not self.partial_configure:
                self.start_tracker_thread(
                    "get_dish_state",
                    [
                        DishMode.OPERATE,
                        (PointingState.TRACK, PointingState.SLEW),
                        ResultCode.OK,
                    ],
                    task_abort_event,
                    self.timeout_id,
                    self.timeout_callback,
                    command_id=self.component_manager.command_id,
                    lrcr_callback=lrcr_callback,
                )
            else:
                self.start_tracker_thread(
                    "get_lrcr_result",
                    [ResultCode.OK],
                    task_abort_event,
                    self.timeout_id,
                    self.timeout_callback,
                    command_id=self.component_manager.command_id,
                    lrcr_callback=lrcr_callback,
                )
            self.logger.info(
                "Command in progress: %s",
                self.component_manager.command_in_progress,
            )

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
                self.component_manager.command_in_progress = None
                return
            if result[0] == ResultCode.OK:
                self.component_manager.command_in_progress = None
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
                self.component_manager.command_in_progress = None
            self.component_manager.command_id = ""
            self.component_manager.partial_configure = False
            self.component_manager.reset_configure_command_ids()
            self.reset_configure_command_result_values()

        except Exception as e:
            self.logger.exception(
                "Exception occurred while updating task status %s", e
            )

    def update_task_callback(
        self: Configure, result_code: ResultCode, exception: str = ""
    ) -> None:
        """
        Method to update task callback.

        :param result_code: result code
        :type result_code: ResultCode
        :param exception: Exception occurred during command execution
        :type exception: str
        :return: None
        :rtype: NoneType.
        """
        if exception:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(result_code, exception),
                exception=exception,
            )
        else:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
            )

        self.component_manager.command_in_progress = ""

    def reset_configure_command_result_values(self: Configure):
        """Method to reset the command result dictionaries for the commands
        ConfigureBand, SetOperateMode, Track and TrackLoadStaticOff"""
        self.set_operate_mode_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }
        self.track_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }
        self.configure_band_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }
        self.track_load_static_off_result = {
            "result_code": None,
            "message": None,
            "exception": None,
            "status": None,
        }

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
                "pointing key is not present in the input json argument.",
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
                self.partial_configure = True
                return self.invoke_trackloadstaticoff(
                    json_argument, reset_offset=reset_offset
                )
            if (
                json_argument["pointing"]["target"]["reference_frame"].lower()
                == "special"
            ):
                target_data = json_argument["pointing"]["target"][
                    "target_name"
                ]
            else:
                target_data = [
                    json_argument["pointing"]["target"]["ra"],
                    json_argument["pointing"]["target"]["dec"],
                ]

            self.component_manager.set_target_data(target_data)

            # Start programTrackTable calculation
            self.component_manager.elevation_limit = True
            self.component_manager.reset_track_process_event()

            # pylint: disable=line-too-long
            self.component_manager.create_process_and_start_track_table_calculation()  # noqa: E501
            # pylint: enable=line-too-long

            receiver_band: str = json_argument["dish"]["receiver_band"]

            # The argin accepted here is a boolean value in accordance
            # with Dish Master
            current_dish_mode: DishMode = self.component_manager.dishMode

            self.logger.info("Invoking ConfigureBand command")

            def _invoke_configure_band_callback(
                status=None,
                progress=None,
                result=None,
                exception=None,
            ):
                """
                Method for invoking ConfigureBand callback
                """
                if result is None:
                    self.logger.info(
                        f"ConfigureBand status: {result}, {exception}, "
                        + f"{status}, {progress}"
                    )
                else:
                    self.configure_band_result["result_code"] = result[0]
                    self.configure_band_result["message"] = result[1]
                    self.configure_band_result["exception"] = exception
                    self.configure_band_result["status"] = status

            self.component_manager.configure_band_command.configure_band(
                argin=receiver_band,
                logger=self.logger,
                task_callback=_invoke_configure_band_callback,
            )

            if self.configure_band_result["result_code"] == ResultCode.FAILED:
                return (
                    self.configure_band_result["result_code"],
                    self.configure_band_result["exception"],
                )

            if self.component_manager.dishMode != DishMode.STOW:
                result_code, message = self.ensure_dish_is_configured(
                    receiver_band,
                    current_dish_mode,
                )
                if result_code[0] in [
                    ResultCode.FAILED,
                    ResultCode.REJECTED,
                    ResultCode.ABORTED,
                ]:
                    return result_code[0], message[0]

                result_code, message = self.start_dish_tracking(json_argument)
                if result_code[0] in [
                    ResultCode.FAILED,
                    ResultCode.REJECTED,
                    ResultCode.ABORTED,
                ]:
                    return result_code[0], message[0]

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
        return result_code[0], message[0]

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
        self.component_manager.command_in_progress = (
            "Configure_TrackLoadStaticOff"
        )
        # Extracting and setting cross elevation offset. Considering
        # 0.0 if the key is omitted

        if reset_offset:
            offsets_argin = RESET_OFFSETS
        else:
            offsets_argin.append(
                input_json["pointing"]["target"].get("ca_offset_arcsec") or 0.0
            )

            # Extracting and setting elevation offset. Considering 0.0 if
            # the key is omitted
            offsets_argin.append(
                input_json["pointing"]["target"].get("ie_offset_arcsec") or 0.0
            )

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
                self.logger.info(
                    f"TrackStaticLoadOff status: {result}, {exception}, "
                    + f"{status}, {progress}"
                )
            else:
                self.track_load_static_off_result["result_code"] = result[0]
                self.track_load_static_off_result["message"] = result[1]
                self.track_load_static_off_result["exception"] = exception
                self.track_load_static_off_result["status"] = status

        # Call the TrackStaticLoadOff command
        command_obj = self.component_manager.track_load_static_off_command
        command_obj.invoke_track_load_static_off(
            argin=json.dumps(offsets_argin),
            logger=self.logger,
            task_callback=_invoke_trackstaticloadoff_callback,
        )

        if (
            self.track_load_static_off_result["result_code"]
            == ResultCode.FAILED
        ):
            return (
                self.track_load_static_off_result["result_code"],
                self.track_load_static_off_result["exception"],
            )

        self.component_manager.command_mapping.setdefault(
            self.component_manager.command_id, {}
        )[
            "message_or_unique_id"
        ] = self.component_manager.trackloadstaticoff_in_progress_id
        self.logger.debug(
            f"command mapping dictionary is: "
            f"{self.component_manager.command_mapping}"
        )

        if reset_offset:
            self.logger.debug(
                "Pointing offsets have been reset to [0.0, 0.0] "
                "and correction key set to %s",
                CORRECTION_KEY.RESET.value,
            )
        self.component_manager.update_source_offset_callback(offsets_argin)
        return ResultCode.OK, ""

    def start_dish_tracking(
        self: Configure, json_argument
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        Invoke Track after waiting for DishMode to Operate

        Args: None

        return: Tuple[ResultCode, str]"""
        if self.component_manager.dishMode != DishMode.OPERATE:
            result_code, message = self.ensure_dish_in_right_dish_mode()
            if result_code[0] in [
                ResultCode.FAILED,
                ResultCode.REJECTED,
                ResultCode.ABORTED,
            ]:
                return result_code, message

        return self.invoke_track_command(json_argument)

    def ensure_dish_is_configured(
        self, receiver_band: str, expected_dish_mode: DishMode
    ) -> Tuple[List[ResultCode], List[str]]:
        """This method check for the completion of configure command

        :param receiver_band: str

        return: Tuple[ResultCode, str]
        """
        # Set wait for dish band to be configured
        result: str = self.set_wait_for_configured_band(receiver_band)
        if result == "ABORTED":
            self.logger.info(
                "AbortCommands() command is invoked on the DishLeafNode."
            )
            return (
                [ResultCode.ABORTED],
                ["AbortCommands() command is invoked on the DishLeafNode."],
            )
        if result == "NOT_ACHIEVED":
            self.logger.error(
                "Timeout occurred while waiting for %s configuredBand in "
                + "Configure command.",
                receiver_band,
            )
            return (
                [ResultCode.FAILED],
                [
                    f"Timeout occurred while waiting for {receiver_band}"
                    + " configuredBand in Configure command."
                ],
            )

        result: str = self.set_wait_for_dishmode(expected_dish_mode)
        if result == "ABORTED":
            self.logger.info(
                "AbortCommands() command is invoked on the DishLeafNode."
            )
            return (
                [ResultCode.ABORTED],
                ["AbortCommands() command is invoked on the DishLeafNode."],
            )

        if result == "NOT_ACHIEVED":
            self.logger.error(
                "Timeout occurred while waiting for dishMode: %s. "
                "ConfigureBand Command failed on the dish manager.",
                expected_dish_mode,
            )
            message = (
                "Timeout occurred while invoking the ConfigureBand() Command."
            )
            return ([ResultCode.FAILED], [message])
        return [ResultCode.OK], [""]

    def ensure_dish_in_right_dish_mode(
        self: Configure,
    ) -> Tuple[List[ResultCode], List[str]]:
        """This method set dish to Operate Mode

        return: Tuple[ResultCode, str]
        """
        self.logger.info("Invoking SetOperateMode command")

        def _invoke_setoperatemode_callback(
            status=None,
            progress=None,
            result=None,
            exception=None,
        ):
            """
            Method for invoking abort callback
            """
            if result is None:
                self.logger.info(
                    f"SetOperateMode status: {result}, {exception}, "
                    + f"{status}, {progress}"
                )
            else:
                self.set_operate_mode_result["result_code"] = result[0]
                self.set_operate_mode_result["message"] = result[1]
                self.set_operate_mode_result["exception"] = exception
                self.set_operate_mode_result["status"] = status

        self.component_manager.setoperatemode_command.set_operate_mode(
            logger=self.logger, task_callback=_invoke_setoperatemode_callback
        )

        if self.set_operate_mode_result["result_code"] == ResultCode.FAILED:
            return (
                [self.set_operate_mode_result["result_code"]],
                [self.set_operate_mode_result["exception"]],
            )

        result: str = self.set_wait_for_dishmode(DishMode.OPERATE)
        if result == "ABORTED":
            self.logger.info(
                "AbortCommands() command is invoked on the DishLeafNode."
            )
            return (
                [ResultCode.ABORTED],
                ["AbortCommands() command is invoked on the DishLeafNode."],
            )
        if result == "NOT_ACHIEVED":
            self.logger.error(
                "Timeout occurred while processing the"
                + " SetOperateMode command."
            )
            return (
                [ResultCode.FAILED],
                [
                    "Timeout occurred while invoking the SetOperateMode "
                    + "command."
                ],
            )
        return [ResultCode.OK], [""]

    def invoke_track_command(
        self: Configure, json_argument
    ) -> Tuple[List[ResultCode], List[str]]:
        """Invoke Track command on dish

        :return: Resulcode and message
        :rtype: tuple
        """
        if self.component_manager.pointingState in [
            PointingState.TRACK,
            PointingState.SLEW,
        ]:
            self.logger.info(
                "Dish is already tracking/slewing. Track() command "
                + "is not invoked."
            )

            self.component_manager.command_mapping.setdefault(
                self.component_manager.command_id, {}
            )["ResultCode"] = ResultCode.OK

            return (
                [ResultCode.OK],
                [
                    "Dish is already in pointingState.TRACK. Track() "
                    + "command is not invoked."
                ],
            )

        result: str = self.is_tracktable_provided()
        if result == "ABORTED":
            self.logger.info(
                "Configure command has been aborted."
                + " Track command is not invoked."
            )
            return ([ResultCode.ABORTED], ["Command has been aborted"])
        if result == "FALSE":
            self.logger.error(
                "Dish manager did not receive TrackTable."
                + "Track() command is not invoked on the Dish."
            )
            return (
                [ResultCode.FAILED],
                [
                    "Dish manager did not receive TrackTable. "
                    + "Track() command is not invoked on the Dish."
                ],
            )

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
                self.logger.info(
                    f"Track status: {result}, {exception}, "
                    + f"{status}, {progress}"
                )
            else:
                self.track_result["result_code"] = result[0]
                self.track_result["message"] = result[1]
                self.track_result["exception"] = exception
                self.track_result["status"] = status

        self.component_manager.track_command.track(
            argin=json_argument,
            logger=self.logger,
            task_callback=_invoke_track_callback,
        )

        if self.track_result["result_code"] == ResultCode.FAILED:
            return (
                [self.track_result["result_code"]],
                [self.track_result["exception"]],
            )

        self.component_manager.command_in_progress = "Track"

        self.component_manager.command_mapping.setdefault(
            self.component_manager.command_id, {}
        )["message_or_unique_id"] = self.component_manager.track_in_progress_id
        self.logger.debug(
            "self.component_manager.command_mapping: %s",
            self.component_manager.command_mapping,
        )

        return [ResultCode.OK], [""]

    def is_tracktable_provided(self) -> str:
        """
        Returns True if programTrackTable is provided to dish.
        """
        flag = "FALSE"
        start_time = time.time()
        elapsed_time = 0
        while elapsed_time < self.component_manager.command_timeout:
            if self.component_manager.abort_event.is_set():
                self.component_manager.abort_event.clear()
                self.logger.info("Abort event is cleared")
                self.logger.info(
                    "AbortCommands() command is invoked while"
                    + " configuring dish."
                )
                flag = "ABORTED"
                return flag
            with self.component_manager.tango_operation_execution_lock:
                track_table = self.dish_master_adapter.programTrackTable
            if len(track_table) > 0:
                flag = "TRUE"
                return flag
            time.sleep(0.1)
            elapsed_time = time.time() - start_time
        return flag
