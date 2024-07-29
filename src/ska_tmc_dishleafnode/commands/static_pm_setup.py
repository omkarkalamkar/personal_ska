"""
StaticPmSetup command class for DishLeafNode.
"""
from __future__ import annotations

import json
import logging
import threading
from logging import Logger
from typing import TYPE_CHECKING, Optional, Tuple

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_telmodel.data import TMData

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE

configure_logging()
LOGGER = logging.getLogger(__name__)
if TYPE_CHECKING:
    from ..manager.component_manager import DishLNComponentManager


class StaticPmSetup(DishLNCommand):
    """
    A class for DishLeafNode's StaticPmSetup() command.

    This command provides an interface to provide global pointing
    data to the dish. This command takes TelModel URI as an input,
    downloads the JSON file for the given version, does validations
    and passes the JSON to its respective dish.
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

    # pylint: disable=unused-argument
    def invoke_static_pm_setup(
        self,
        argin: str,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        # pylint: enable=unused-argument
        """A method to invoke the do method of the StaticPmSetup command
        class. This method also updates the task callback according to command
        status.

        :param argin: Input argument containing the TelModel JSON URI

        :type argin: str
        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        :return: : None
        :rtype: None
        """
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        result_code, message = self.do(argin)
        self.component_manager.command_in_progress = "StaticPmSetup"
        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(result_code, message),
                exception=Exception(message),
            )
            self.component_manager.command_in_progress = ""
        else:
            logger.info(
                "The StaticPmSetup command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
            )

    def get_global_pointing_data_json(
        self, initial_params: dict
    ) -> Tuple[dict, str]:
        """Get global pointing data json from initial params
        :param initial_param: this param containing tm data source uri
        and file path used to get the global pointing data.
        """
        data_sources = initial_params.get("tm_data_sources", None)
        tm_data_filepath = initial_params.get("tm_data_filepath", None)
        if data_sources and tm_data_filepath:
            try:
                data = TMData(data_sources, update=True)
                return data[tm_data_filepath].get_dict(), ""
            except Exception as e:
                self.logger.exception(
                    "Error in Loading global pointing data json file %s", e
                )
                return (
                    {},
                    f"Error in Loading global pointing data json file {e}",
                )
        return {}, "tm_data_sources and tm_data_filepath not provided in json"

    def validate_gpm_json(self, input_json) -> Tuple[bool, str]:
        """The purpose of this method is to do the desired validations
        on the provided global pointing model json

        param input_json: JSON containing GPM data
        return:
            boolean
        """

        if (
            input_json["Antenna"].lower()
            != self.component_manager.dish_id.lower()
        ):
            message = (
                f"Global pointing antenna {input_json['Antenna']} is"
                f"not matching with Dish ID {self.component_manager.dish_id}"
            )
            self.logger.info(message)
            return (False, message)

        return True, ""

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke StaticPmSetup command on DishMaster.

        param argin: String containing global pointing data

        return:
            (ResultCode, str)
        """

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.info(
                "%s adapter not found", self.component_manager.dish_dev_name
            )
            return result_code, message

        (
            global_pointing_data_json,
            message,
        ) = self.get_global_pointing_data_json(json.loads(argin))

        if "Error in Loading" in message or "not provided in json" in message:
            return ResultCode.REJECTED, "Invalid TelModel path"

        self.logger.debug(
            "Global pointing data JSON: %s", global_pointing_data_json
        )

        result, message = self.validate_gpm_json(global_pointing_data_json)
        if result:
            with self.component_manager.tango_operation_execution_lock:
                result_code, message = self.call_adapter_method(
                    "Dish Master",
                    self.dish_master_adapter,
                    "StaticPmSetup",
                    argin=json.dumps(global_pointing_data_json),
                )
                return result_code[0], message[0]

        return ResultCode.REJECTED, message
