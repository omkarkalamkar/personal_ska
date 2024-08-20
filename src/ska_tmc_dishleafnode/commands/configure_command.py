"""
Configure class for DishLeafNode.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from logging import Logger
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

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

if TYPE_CHECKING:
    from ..manager.component_manager import DishLNComponentManager


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
        component_manager: DishLNComponentManager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )

        self.track_table_process = None
        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback = TimeoutCallback(self.timeout_id, self.logger)
        self.task_callback: Callable
        self.partial_configure = False

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
        # Indicate that the task has started
        self.logger.info("Invoke Configure command -----")
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
        logger.info("Return lrcr_callback: %s", lrcr_callback)
        logger.info("Return Code: %s", return_code)
        logger.info("message: %s", message)
        if return_code == ResultCode.FAILED:
            logger.info(
                "Setting taskcallback to FAILED with message: %s",
                lrcr_callback,
            )
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(return_code, message),
                exception=message,
            )
            self.component_manager.command_in_progress = ""
        else:
            logger.info(
                "self.component_manager.command_in_progress: %s",
                self.component_manager.command_in_progress,
            )
            if (
                self.component_manager.command_in_progress
                not in self.component_manager.supported_commands
            ):
                self.component_manager.command_in_progress = ""
                logger.info(
                    "self.component_manager.command_in_progress: %s",
                    self.component_manager.command_in_progress,
                )
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

            logger.info(
                "The Configure command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )

    def update_task_status(self, **kwargs) -> None:
        """Method to update task status with result code and exception message
        if any."""
        try:
            result = kwargs.get("result")
            status = kwargs.get("status", TaskStatus.COMPLETED)
            message = kwargs.get("exception")

            if result[0] == ResultCode.OK:
                self.component_manager.command_in_progress = None
                self.task_callback(result=result, status=status)
            elif status == TaskStatus.ABORTED:
                self.task_callback(status=status)
                return
            else:
                self.logger.info(
                    "TIMEOUT occurred: %s, %s, %s", result, status, message
                )
                self.task_callback(
                    status=TaskStatus.COMPLETED,
                    result=result,
                    exception=message,
                )
                self.component_manager.command_in_progress = None
            self.component_manager.command_id = ""
            self.partial_configure = False

        except Exception as e:
            self.logger.exception(
                "Exception occured while updating task status %s", e
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
            self.logger.info("Configure command started.")
            result_code, message = self.init_adapter()
            if result_code == ResultCode.FAILED:
                self.logger.error(
                    "Adapter for device : %s is not found ",
                    self.component_manager.dish_dev_name,
                )
                return result_code, message

            json_argument = json.loads(argin)
            # Start programTrackTable calculation
            self.component_manager.elevation_limit = True
            self.component_manager.reset_track_process_event()
            reset_offset = (
                self.component_manager.correction_key
                == CORRECTION_KEY.RESET.value
            )
            if reset_offset and "tmc" not in json_argument:
                # self.partial_configure = True
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
            command_name: str = f"ConfigureBand{receiver_band}"
            # The argin accepted here is a boolean value in accordance
            # with Dish Master
            current_dish_mode: DishMode = self.component_manager.dishMode

            with self.component_manager.tango_operation_execution_lock:
                result_code, message = self.call_adapter_method(
                    "Dish Master",
                    self.dish_master_adapter,
                    command_name,
                    True,
                )
            if (
                self.component_manager.dishMode != DishMode.STOW
                and result_code[0] not in [ResultCode.FAILED]
            ):
                result_code, message = self.ensure_dish_is_configured(
                    receiver_band, current_dish_mode
                )
                if result_code[0] in [ResultCode.FAILED, ResultCode.REJECTED]:
                    return result_code[0], message[0]

                result_code, message = self.start_dish_tracking()
                if result_code[0] in [ResultCode.FAILED, ResultCode.REJECTED]:
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
        self.logger.info("Result code: %s", result_code[0])
        self.logger.info("message: %s", message[0])
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
        self.logger.info("invoke trackstaticoff method ------")
        offsets_argin = []
        self.component_manager.command_in_progress = (
            "Configure_TrackLoadStaticOff"
        )
        self.logger.info(
            "self.component_manager.command_in_progress: %s",
            self.component_manager.command_in_progress,
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

        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master",
                self.dish_master_adapter,
                "TrackLoadStaticOff",
                offsets_argin,
            )
            # message[0] should be command_id and result[0] should
            # be ResultCode
            self.logger.info(
                "result_code[0]: %s, result_code[0]: %s",
                result_code,
                result_code[0],
            )
            if result_code[0] in [ResultCode.QUEUED, ResultCode.OK]:
                self.component_manager.command_mapping.setdefault(
                    self.component_manager.command_id, {}
                )["message_or_unique_id"] = message[0]
                self.logger.info(f"message[0]: {message[0]}")
                self.logger.info(
                    f"component_manager.command_mapping -"
                    f"{self.component_manager.command_mapping}"
                )

        if reset_offset:
            self.logger.debug(
                "Pointing offsets have been reset to [0.0, 0.0] "
                "and correction key set to %s",
                CORRECTION_KEY.RESET.value,
            )
        self.component_manager.update_source_offset_callback(offsets_argin)
        return result_code[0], message[0]

    def start_dish_tracking(
        self: Configure,
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        Invoke Track after waiting for DishMode to Operate

        Args: None

        return: Tuple[ResultCode, str]"""
        if self.component_manager.dishMode != DishMode.OPERATE:
            result_code, message = self.ensure_dish_in_right_dish_mode()
            if result_code[0] in [ResultCode.FAILED, ResultCode.REJECTED]:
                return result_code, message

        return self.invoke_track_command()

    def ensure_dish_is_configured(
        self, receiver_band: str, expected_dish_mode: DishMode
    ) -> Tuple[List[ResultCode], List[str]]:
        """This method check for the completion of configure command

        :param receiver_band: str

        return: Tuple[ResultCode, str]
        """
        # Set wait for dish band to be configured
        result: bool = self.set_wait_for_configured_band(receiver_band)
        if not result:
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
        result: bool = self.set_wait_for_dishmode(expected_dish_mode)
        if not result:
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
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "SetOperateMode"
            )
        if result_code[0] in [ResultCode.FAILED, ResultCode.REJECTED]:
            return result_code, message

        result: bool = self.set_wait_for_dishmode(DishMode.OPERATE)
        if not result:
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
        self: Configure,
    ) -> Tuple[List[ResultCode], List[str]]:
        """Invoke Track command on dish

        :return: Resulcode and message
        :rtype: tuple
        """
        result: bool = self.is_tracktable_provided()
        if not result:
            self.logger.error(
                "Timed out while waiting to generate TrackTable."
                + "Track command will not be invoked on the Dish."
            )
            return (
                [ResultCode.FAILED],
                [
                    "Timeout occurred while waiting to "
                    + " generate programTrackTable."
                ],
            )

        with self.component_manager.tango_operation_execution_lock:
            self.component_manager.command_in_progress = "Track"
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Track"
            )
            # message[0] should be command_id and result[0] should be
            # ResultCode
            self.component_manager.logger.info(
                "result code in %s", result_code[0]
            )
            # if result_code[0] in [ResultCode.QUEUED, ResultCode.OK]:
            self.component_manager.command_mapping.setdefault(
                self.component_manager.command_id, {}
            )["message_or_unique_id"] = message[0]
            self.logger.info(f"message[0]: {message[0]}")
            self.logger.info(
                f"component_manager.command_mapping -"
                f"{self.component_manager.command_mapping}"
            )

        if result_code[0] in [ResultCode.FAILED, ResultCode.REJECTED]:
            self.logger.error(f"Track Invocation Failed , Reason: {message}")
            return result_code, message

        self.logger.info("Invoked Track command successfully on dish.")
        return result_code, message

    def is_tracktable_provided(self) -> bool:
        """
        Returns True if programTrackTable is provided to dish.
        """
        start_time = time.time()
        elapsed_time = 0
        while elapsed_time < self.component_manager.command_timeout:
            with self.component_manager.tango_operation_execution_lock:
                track_table = self.dish_master_adapter.programTrackTable
            if len(track_table) > 0:
                return True
            time.sleep(0.1)
            elapsed_time = time.time() - start_time
        return False
