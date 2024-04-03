"""
Configure class for DishLeafNode.
"""
import json
import logging
import threading
import time
from logging import Logger
from typing import Optional, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.enum import DishMode

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import (
    TRACK_COMMAND_TIMEOUT,
    TRACK_TABLE_ENTRY_SIZE,
)

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
        self,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.task_callback = None
        self.tracking_thread = None

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

        Args:-> Tuple[ResultCode, str]
            result_code (ResultCode): result code
            exception (str, optional): Exception occurred during command
            execution. Defaults to "".
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
    def validate_json_argument(self, input_argin: dict) -> tuple:
        """Validates the json argument"""

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

        return:
            (ResultCode, str)

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
                result_code, message = self.call_adapter_method(
                    "Dish Master",
                    self.dish_master_adapter,
                    "TrackLoadStaticOff",
                    offsets_argin,
                )
                return result_code[0], message[0]

            receiver_band = json_argument["dish"]["receiver_band"]
            ra_value = json_argument["pointing"]["target"]["ra"]
            dec_value = json_argument["pointing"]["target"]["dec"]

            # Start programTrackTable calculation
            self.component_manager.elevation_limit = True
            self.component_manager.event_track_time.clear()
            self.tracking_thread = threading.Thread(
                target=self.component_manager.track_thread,
                args=[ra_value, dec_value, self],
            )
            if not self.tracking_thread.is_alive():
                self.tracking_thread.start()

            current_dish_mode = self.component_manager.dishMode
            command_name = f"ConfigureBand{receiver_band}"
            # The argin accepted here is a boolean value in accordance
            # with Dish Master
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, command_name, True
            )

            if (
                current_dish_mode != DishMode.STOW
                and result_code[0] != ResultCode.FAILED
            ):
                result_code, message = self.ensure_dish_is_configured(
                    receiver_band
                )
                if result_code == ResultCode.FAILED:
                    return result_code, message
                result_code, message = self.start_dish_tracking(
                    current_dish_mode
                )
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

    def start_dish_tracking(self, current_dish_mode) -> Tuple[ResultCode, str]:
        """
        Invoke Track after waiting for DishMode to Operate

        Args:
        current_dish_mode (DishMode): The current dish mode.

        return: Tuple[ResultCode, str]"""
        if current_dish_mode == DishMode.STANDBY_FP:
            result_code, message = self.ensure_dish_in_right_dish_mode()
            if result_code == ResultCode.FAILED:
                return result_code, message
        # start tracking thread
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

        return: Tuple[ResultCode, str]
        """
        # Wait until 2 set of programTrackTable entries are reached
        start_time = time.time()
        while (time.time() - start_time) < TRACK_COMMAND_TIMEOUT:
            if (
                len(self.dish_master_adapter.programTrackTable)
                >= 2
                * TRACK_TABLE_ENTRY_SIZE
                * self.component_manager.track_table_entries
            ):
                break
            time.sleep(0.5)

        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "Track"
        )
        if result_code[0] == ResultCode.FAILED:
            self.logger.error(f"Track Invocation Failed {message}")
            return result_code[0], message[0]

        self.logger.info("Invoked Track command successfully on dish.")
        return result_code[0], message[0]
