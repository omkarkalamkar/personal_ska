"""
Configure class for DishLeafNode.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from logging import Logger
from typing import TYPE_CHECKING, List, Optional, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.enum import DishMode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE

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
        self.task_callback = None
        self.track_table_process = None

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
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        self.component_manager.command_in_progress = "Configure"
        return_code, message = self.do(argin)

        if return_code == ResultCode.FAILED:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(return_code, message),
                exception=message,
            )
            self.component_manager.command_in_progress = ""
        else:
            logger.info(
                "The Configure command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )
            if (
                self.component_manager.command_in_progress
                != "Configure_TrackLoadStaticOff"
            ):
                self.component_manager.command_in_progress = ""
                self.task_callback(
                    status=TaskStatus.COMPLETED,
                    result=(ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
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

            if json_argument.get("tmc"):
                return self.invoke_trackloadstaticoff(json_argument)

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

            self.component_manager.target_data = target_data
            self.component_manager.dish_adapter = self.dish_master_adapter
            try:
                if not self.component_manager.track_table_process.is_alive():
                    self.component_manager.track_table_process.start()
            except Exception as exception:
                self.logger.error(
                    "Exception occurred while starting programTrackTable "
                    "calculation: %s",
                    exception,
                )

            receiver_band = json_argument["dish"]["receiver_band"]
            command_name = f"ConfigureBand{receiver_band}"
            # The argin accepted here is a boolean value in accordance
            # with Dish Master
            current_dish_mode = self.component_manager.dishMode

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
        return result_code[0], message[0]

    def invoke_trackloadstaticoff(
        self: Configure, input_json: dict
    ) -> Tuple[ResultCode, str]:
        """Extracts the offsets from input json and invokes the
        TrackLoadStaticOff command on DishMaster device.

        :param input_json: Input json for Configure command
        :type input_json: dict

        :returns: Tuple[ResultCode, str]
        """
        self.component_manager.command_in_progress = (
            "Configure_TrackLoadStaticOff"
        )
        # Extracting and setting cross elevation offset. Considering
        # 0.0 if the key is omitted
        ca_offset = (
            input_json["pointing"]["target"].get("ca_offset_arcsec") or 0.0
        )

        # Extracting and setting elevation offset. Considering 0.0 if
        # the key is omitted
        ie_offset = (
            input_json["pointing"]["target"].get("ie_offset_arcsec") or 0.0
        )

        offsets_argin = [ca_offset, ie_offset]
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master",
                self.dish_master_adapter,
                "TrackLoadStaticOff",
                offsets_argin,
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
        result = self.set_wait_for_configured_band(receiver_band)
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
        result = self.set_wait_for_dishmode(expected_dish_mode)
        if not result:
            self.logger.error(
                "Timeout occurred while waiting for dishMode: %s. "
                "ConfigureBand Command failed on the dish manager.",
                expected_dish_mode,
            )
            message = (
                "Timeout occurred while invoking the "
                + f"ConfigureBand{receiver_band}() Command."
            )
            return (ResultCode.FAILED, message)
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

        result = self.set_wait_for_dishmode(DishMode.OPERATE)
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
        result = self.is_tracktable_provided()
        if not result:
            self.logger.error(
                "Cannot invoke Track command on the Dish since track "
                "table is not provided"
            )
        else:
            self.logger.info(
                "TrackTable is provided to dish, "
                "proceeding towards Track() command execution"
            )

        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Track"
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
        self.logger.info("Start time: %s", start_time)
        elapsed_time = 0
        while elapsed_time < self.component_manager.command_timeout:
            if self.component_manager.get_track_table_provided() is True:
                self.logger.info("Tracktable flag is True")
                return True
            time.sleep(0.2)
            self.logger.info(
                "Track table flag: %s",
                self.component_manager.get_track_table_provided(),
            )
            elapsed_time = time.time() - start_time
        self.logger.error("Time out while waiting to generate TrackTable")
        return False
