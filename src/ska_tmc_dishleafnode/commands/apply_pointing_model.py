"""
ApplyPointingModel command class for DishLeafNode.

This module contains the implementation of the ApplyPointingModel command
for the DishLeafNode component. It provides functionality to apply a
pointing model to the dish based on the provided TelModel URI.
"""
from __future__ import annotations

import json
import logging
import threading
from logging import Logger
from typing import TYPE_CHECKING, Tuple

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


class ApplyPointingModel(DishLNCommand):
    """
    A class for DishLeafNode's ApplyPointingModel() command.
    Its a dummy command at present.
    Will be renamed, once Dish ICD gets updated.

    This command provides an interface to provide global pointing
    data to the dish. This command takes TelModel URI as an input,
    downloads the JSON file for the given version, does validations
    and passes the JSON to its respective dish.
    """

    def __init__(
        self: ApplyPointingModel,
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
    def invoke_apply_pointing_model(
        self: ApplyPointingModel,
        argin: str,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: threading.Event,
    ) -> None:
        # pylint: enable=unused-argument
        """A method to invoke the do method of the ApplyPointingModel command
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
        :return: None
        :rtype: None
        """

        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        self.component_manager.command_in_progress = "ApplyPointingModel"

        result_code, message = self.do(argin)

        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(result_code, message),
                exception=Exception(message),
            )
            self.component_manager.command_in_progress = ""
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
            )
            logger.info(
                "The ApplyPointingModel command invoked successfully %s",
                self.dish_master_adapter.dev_name,
            )

    def get_global_pointing_data_json(
        self: ApplyPointingModel, initial_params: dict
    ) -> Tuple[dict, str]:
        """Get global pointing data json from initial params with a timeout.
        This method downloads the JSON, from the given TelModel path.

        :param initial_param: contains tm data source URI and file path
        used to get the global pointing data.

        :return: dictionary in downloaded JSON and message string if any
        :rtype: Tuple[dict, str]
        """
        tm_data_sources = initial_params.get("tm_data_sources", None)
        tm_data_filepath = initial_params.get("tm_data_filepath", None)

        if not tm_data_sources or not tm_data_filepath:
            return (
                {},
                "Provide both tm data sources and tm data filepath in input"
                + " paramter",
            )

        result = {}
        message = ""

        # Function to execute data retrieval within a thread
        def retrieve_data():
            nonlocal result, message
            try:
                data = TMData(tm_data_sources, update=True)
                result, message = data[tm_data_filepath].get_dict(), ""
            except json.JSONDecodeError as json_error:
                self.logger.exception("JSON Error: %s", json_error)
                result, message = {}, f"JSON Error: {json_error}"
            except Exception as exception:
                self.logger.exception(
                    "Error in Loading global pointing data json file %s",
                    exception,
                )
                result, message = (
                    {},
                    "Error in Loading global pointing"
                    + " data json file {exception}",
                )

        # Set up a thread for data retrieval
        data_thread = threading.Thread(target=retrieve_data)
        data_thread.start()
        data_thread.join(timeout=10)  # Wait for up to 10 seconds

        # Check if the thread is still active after the timeout
        if data_thread.is_alive():
            message = "URI not reachable (timeout)"
            result = {}
            data_thread.join()  # Optional cleanup, forcefully ends the thread

        return result, message

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self: ApplyPointingModel, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke ApplyPointingModel command on DishMaster.
        Example JSON:
        {
        "interface":
        "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0",
        "tm_data_sources":
        ["car://gitlab.com/ska-telescope/ska-tmc/
        ska-tmc-simulators?main#tmdata"],
        "tm_data_filepath":
        "instrument/ska_mid1/global_pointing_model_data/
        global_pointing_model.json"
        }

        param argin: Global pointing model data JSON

        return:(ResultCode, str)
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

        if message:
            return ResultCode.FAILED, message

        self.logger.debug(
            "Global pointing data JSON: %s", global_pointing_data_json
        )

        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master",
                self.dish_master_adapter,
                "ApplyPointingModel",
                argin=json.dumps(global_pointing_data_json),
            )
            return result_code[0], message[0]

        return result_code, message
