"""
Configure class for DishLeafNode.
"""
from __future__ import annotations

import json
import logging
import threading
from logging import Logger
from multiprocessing import Process
from typing import TYPE_CHECKING, Optional, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.enum import DishMode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

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
        self,
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
        self,
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
        logger.info(message)
        logger.info(return_code)

        if return_code == ResultCode.FAILED:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(return_code),
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
                    result=ResultCode(return_code),
                )

    def update_task_callback(
        self, result_code: ResultCode, exception: str = ""
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
                result=result_code,
                exception=exception,
            )
        else:
            self.task_callback(status=TaskStatus.COMPLETED, result=result_code)
        self.component_manager.command_in_progress = ""

    # pylint: enable=unused-argument
    def validate_json_argument(
        self, input_argin: dict
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
    def do(self, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke Configure command on dish.

        :param argin:
            A String in a JSON format that includes pointing parameters
            of Dish- Azimuth and
            Elevation Angle.

                Example:
                {"pointing":{"target":{"system":"ICRS",
                "name":"Polaris Australis",
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
                self.logger.info(
                    "%s adapter not found ",
                    self.component_manager.dish_dev_name,
                )
                return result_code, message

            json_argument = json.loads(argin)
            # Start programTrackTable calculation
            self.component_manager.elevation_limit = True
            self.component_manager.reset_track_process_event()

            if not json_argument.get("tmc"):
                ra_value = json_argument["pointing"]["target"]["ra"]
                dec_value = json_argument["pointing"]["target"]["dec"]
                self.track_table_process = Process(
                    target=self.component_manager.track_process,
                    args=[ra_value, dec_value, self],
                )
                if not self.track_table_process.is_alive():
                    self.track_table_process.start()

            if json_argument.get("tmc"):
                self.component_manager.command_in_progress = (
                    "Configure_TrackLoadStaticOff"
                )
                # Extracting and setting cross elevation offset. Considering
                # 0.0 if the key is omitted
                ca_offset = (
                    json_argument["pointing"]["target"].get("ca_offset_arcsec")
                    or 0.0
                )

                # Extracting and setting elevation offset. Considering 0.0 if
                # the key is omitted
                ie_offset = (
                    json_argument["pointing"]["target"].get("ie_offset_arcsec")
                    or 0.0
                )

                offsets_argin = [ca_offset, ie_offset]
                with self.component_manager.tango_operation_execution_lock:
                    result_code, message = self.call_adapter_method(
                        "Dish Master",
                        self.dish_master_adapter,
                        "TrackLoadStaticOff",
                        offsets_argin,
                    )
                self.component_manager.update_source_offset_callback(
                    offsets_argin
                )
                return result_code[0], message[0]

            receiver_band = json_argument["dish"]["receiver_band"]
            command_name = f"ConfigureBand{receiver_band}"
            # The argin accepted here is a boolean value in accordance
            # with Dish Master
            with self.component_manager.tango_operation_execution_lock:
                result_code, message = self.call_adapter_method(
                    "Dish Master", self.dish_master_adapter, command_name, True
                )

            if (
                self.component_manager.dishMode != DishMode.STOW
                and result_code[0] != ResultCode.FAILED
            ):
                result_code, message = self.ensure_dish_is_configured(
                    receiver_band
                )
                if result_code == ResultCode.FAILED:
                    return result_code, message
                result_code, message = self.start_dish_tracking()
                if result_code == ResultCode.FAILED:
                    return result_code, message

        except Exception as exception:
            self.logger.exception(f"Command invocation failed: {exception}")
            return (
                ResultCode.FAILED,
                "The invocation of the Configure command is failed on"
                + f" Dish Master Device {self.dish_master_adapter.dev_name}."
                + "Reason: Error in calling the Configure command on"
                + f" Dish Master: {exception}",
            )
        return result_code, message

    def start_dish_tracking(self) -> Tuple[ResultCode, str]:
        """
        Invoke Track after waiting for DishMode to Operate

        Args: None

        return: Tuple[ResultCode, str]"""
        if self.component_manager.dishMode != DishMode.OPERATE:
            result_code, message = self.ensure_dish_in_right_dish_mode()
            if result_code == ResultCode.FAILED:
                return result_code, message

        result_code, message = self.invoke_track_command()
        return result_code, message

    def ensure_dish_is_configured(
        self, receiver_band: str
    ) -> Tuple[ResultCode, str]:
        """This method check for the completion of configure command

        :param receiver_band: str

        return: Tuple[ResultCode, str]
        """
        # Set wait for dish band to be configured
        result = self.set_wait_for_configured_band(receiver_band)
        if not result:
            self.logger.error(
                "Timeout occurred while waiting for %s configuredBand in "
                + "Configure Command.",
                receiver_band,
            )
            return (
                ResultCode.FAILED,
                f"Timeout occurred while waiting for {receiver_band}"
                + " configuredBand in Configure Command.",
            )
        return ResultCode.OK, ""

    def ensure_dish_in_right_dish_mode(self) -> Tuple[ResultCode, str]:
        """This method set dish to Operate Mode

        return: Tuple[ResultCode, str]
        """
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "SetOperateMode"
            )
        if result_code[0] == ResultCode.FAILED:
            return result_code[0], message[0]

        result = self.set_wait_for_dishmode(DishMode.OPERATE)
        if not result:
            self.logger.error(
                "Timeout occurred while invoking the SetOperateMode Command."
            )
            return (
                ResultCode.FAILED,
                "Timeout occurred while invoking the SetOperateMode Command.",
            )
        return ResultCode.OK, ""

    def invoke_track_command(self) -> Tuple[ResultCode, str]:
        """Invoke Track command on dish

        :return: Resulcode and message
        :rtype: tuple
        """
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "Track"
            )
        if result_code[0] == ResultCode.FAILED:
            self.logger.error(f"Track Invocation Failed {message}")
            return result_code[0], message[0]

        self.logger.info("Invoked Track command successfully on dish.")
        return result_code[0], message[0]
