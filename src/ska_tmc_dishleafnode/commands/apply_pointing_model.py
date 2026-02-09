"""
ApplyPointingModel command class for DishLeafNode.

This module contains the implementation of the ApplyPointingModel command
for the DishLeafNode component. It provides functionality to apply a
pointing model to the dish based on the provided TelModel URI.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import urllib
from typing import TYPE_CHECKING, Optional, Tuple

# from ska_tango_base.executor import TaskStatus
from ska_control_model import TaskStatus
from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_telmodel.data import TMData

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

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
        self.band: str = ""
        self.band_version: str = ""
        self.previous_band_version: str = ""

    def update_task_callback(
        self,
        result_code: ResultCode,
        message: str,
        task_callback: TaskCallbackType,
    ) -> None:
        """Updates task status and GPM version based on command result.

        Args
        ----
        result_code : ResultCode
            Command result status code
        message : str
            Status description
        task_callback : TaskCallbackType
            Callback for task status updates
        """

        try:
            if result_code != int(ResultCode.OK):
                self.logger.info(
                    "ApplyPointingModel command failed on %s and message: %s",
                    self.component_manager.dish_dev_name,
                    message,
                )
                if self.band:
                    self.component_manager.gpm_version[
                        self.band.capitalize()
                    ] = self.previous_band_version
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result=(ResultCode(result_code), message),
                    exception=message,
                )
            else:
                self.logger.info(
                    "ApplyPointingModel command invoked successfully"
                    " on %s for band: %s, version: %s and "
                    " message received is: %s",
                    self.component_manager.dish_dev_name,
                    self.band,
                    self.band_version,
                    message,
                )

                self.logger.debug(
                    "Updating GPM version: %s",
                    self.component_manager.gpm_version,
                )
                self.component_manager.handle_gpm_version_callback(
                    json.dumps(self.component_manager.gpm_version)
                )
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result=(ResultCode(result_code), message),
                )
        except Exception as e:
            self.logger.exception("Error updating GPM version: %s", str(e))
        self.component_manager.command_in_progress = ""
        self.previous_band_version = ""
        self.band = ""
        self.band_version = ""

    # pylint: disable=unused-argument
    def invoke_apply_pointing_model(
        self: ApplyPointingModel,
        argin: str,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """A method to invoke the do method of the ApplyPointingModel command
        class. This method also updates the task callback according to command
        status.

        :param argin: Input argument containing the TelModel JSON URI

        :type argin: str
        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType
        :return: None
        :rtype: None
        """

        # 1. QUEUED (MANDATORY)
        # task_callback(status=TaskStatus.QUEUED)

        task_callback(status=TaskStatus.IN_PROGRESS)

        self.component_manager.command_in_progress = "ApplyPointingModel"
        result_code, message = self.do(argin)
        # result_code, message = self.do(argin=argin)
        # result_code, message = self.do(logger=self.logger, argin=argin)
        self.logger.info("ResultCode: %s Message: %s", result_code, message)
        self.update_task_callback(result_code, message, task_callback)

    # pylint: enable=unused-argument

    def get_global_pointing_data_json(
        self: ApplyPointingModel, tm_data_sources, tm_data_filepath
    ) -> Tuple[dict, str]:
        """Get global pointing data json from initial params with a timeout.
        This method downloads the JSON, from the given TelModel path.

        :param initial_param: contains tm data source URI and file path
                                used to get the global pointing data.

        :return: dictionary in downloaded JSON and message string if any
        :rtype: Tuple[dict, str]
        """

        result = {}
        message = ""

        # Function to execute data retrieval within a thread
        def retrieve_data():
            """Fetch JSON data from GPM repo and return as a dictionary."""
            nonlocal result, message
            try:
                tmdata = TMData(tm_data_sources)
                file_name = tm_data_filepath.split('/')[-1]
                gpm_dir_path = tm_data_filepath.rsplit('/', 1)[0]
                self.logger.debug("GPM dir path: %s", gpm_dir_path)
                gpm_dir = tmdata[gpm_dir_path]
                self.logger.debug("Files found on GPM repo: %s", list(gpm_dir))
                matches = [
                    f for f in list(gpm_dir) if f.lower() == file_name.lower()
                ]
                if not matches:
                    message = (
                        f"{file_name} not found on "
                        f"{tm_data_sources[0]}/{gpm_dir_path}"
                    )
                    self.logger.error("Error: %s", message)
                    return
                if len(matches) > 1:
                    if file_name in matches:
                        matches[0] = file_name
                    self.logger.error(
                        "Multiple files %s found for %s, applying: %s",
                        matches,
                        file_name,
                        matches[0],
                    )
                gpm_file = tmdata[f"{gpm_dir_path}/{matches[0]}"]
                result, message = gpm_file.get_dict(), ""
            except json.JSONDecodeError as json_error:
                self.logger.error(
                    "Failed to parse JSON ,Error: %s", str(json_error)
                )
                result, message = {}, f"JSON Error: {json_error}"
            except Exception as exception:
                self.logger.exception(
                    "Exception occured in loading global pointing data "
                    + "JSON file. Exception: %s",
                    str(exception),
                )
                result, message = (
                    {},
                    "Error in loading global pointing"
                    + f" data json file {str(exception)}",
                )

        # Set up a thread for data retrieval
        data_thread = threading.Thread(target=retrieve_data)
        data_thread.start()
        data_thread.join(timeout=10)  # Wait for up to 10 seconds

        # Check if the thread is still active after the timeout
        if data_thread.is_alive():
            # Add tm_data_sources + file_path in message
            message = "URI not reachable (timeout)"
            result = {}
            data_thread.join()  # Optional cleanup, forcefully ends the thread

        return result, message

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self: ApplyPointingModel, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke ApplyPointingModel command on DishMaster.

        Args:
            argin (str): Global pointing model data JSON

        .. literalinclude:: ../../../../tests/data/global_pointing_model.json
            :language: json
            :caption: Example JSON for ApplyPointingModel

        Note:
            Enter input json without spaces.

        Returns:
            Tuple[ResultCode, str]: Tuple of ResultCode and message.

        """
        try:
            result_code = ResultCode.UNKNOWN
            message = ""
            # gpm_json_data = json.loads(argin)
            try:
                gpm_json_data = json.loads(argin)
            except (json.JSONDecodeError, TypeError) as exc:
                self.logger.error("JSON parsing failed: %s", exc)
                return ResultCode.FAILED, f"JSON Error: {exc}"
            tm_data_sources = gpm_json_data.get("tm_data_sources", None)
            tm_data_filepath = gpm_json_data.get("tm_data_filepath", None)
            self.logger.info(
                "GPM paths received -> tm_data_sources: %s "
                "tm_data_filepath: %s",
                tm_data_sources,
                tm_data_filepath,
            )
            if not all([tm_data_sources, tm_data_filepath]):
                return (
                    ResultCode.FAILED,
                    "Error: Found empty/None field in required keys "
                    + f"tm_data sources: {tm_data_sources} and "
                    + f"tm_data_filepath: {tm_data_filepath}",
                )
            result_code, message = self.init_adapter()
            if result_code == ResultCode.FAILED:
                self.logger.debug(
                    "Failed to find adapter for device: %s",
                    self.component_manager.dish_dev_name,
                )
                return result_code, message

            if isinstance(tm_data_sources, str):
                tm_data_sources = [tm_data_sources]

            (
                global_pointing_data_json,
                return_message,
            ) = self.get_global_pointing_data_json(
                tm_data_sources, tm_data_filepath
            )

            if return_message:
                self.logger.error(
                    "GPM error message: %s",
                    return_message,
                )
                return ResultCode.FAILED, return_message

            self.logger.debug(
                "Sending GPM json to dish: %s", global_pointing_data_json
            )

            with self.component_manager.tango_operation_execution_lock:
                self.band, self.band_version = self.extract_band_and_version(
                    gpm_json_data
                )
                self.previous_band_version = (
                    self.component_manager.gpm_version.get(
                        self.band.capitalize()
                    )
                )
                self.component_manager.gpm_version[
                    self.band.capitalize()
                ] = self.band_version
                self.logger.debug(
                    "Previous band version: %s", self.previous_band_version
                )
                # Set and memorize the tmdata paths at the
                # time of initialization
                if (
                    not self.component_manager.gpm_source_path
                    or not self.component_manager.gpm_file_path
                ):
                    self.component_manager.gpm_source_path = tm_data_sources[
                        0
                    ].split("?")[0]
                    self.component_manager.gpm_file_path = re.split(
                        r'band', tm_data_filepath, flags=re.IGNORECASE
                    )[0]
                    self.component_manager.store_gpm_path_data_callback(
                        self.component_manager.gpm_source_path,
                        self.component_manager.gpm_file_path,
                    )
                self.logger.debug(
                    "Applying GPM on band: %s with version: %s",
                    self.band,
                    self.band_version,
                )
                result_code, message = self.call_adapter_method(
                    "Dish Master",
                    self.dish_master_adapter,
                    "ApplyPointingModel",
                    argin=json.dumps(global_pointing_data_json),
                )
                return result_code[0], message[0]
        except Exception as e:
            self.logger.exception(
                "Exception occurred while executing Apply Pointing Model"
                + "on dish: %s",
                str(e),
            )
            result_code = ResultCode.FAILED
            message = f"Exception occurred: {e}"
        return result_code, message

    def extract_band_and_version(self, gpm_data: dict) -> Tuple[str, str]:
        """
        Extract the band and version from the GPM metadata JSON.

        Args:
            gpm_data (dict): The parsed GPM metadata JSON.
            Expected to contain keys for the file path (to determine the band)
            and the interface (to determine the version).

        Returns:
            Tuple[str, str]: A tuple containing:
                - band (str): The band extracted from the file path.
                - version (str): The version extracted from the interface.
        """
        band, version = "", ""
        try:
            # Band from filepath (support Band_1, Band_5a, Band_5b, etc.)
            filepath = gpm_data.get("tm_data_filepath", "")
            band_match = re.search(r"Band_[1-4]|Band_5[abAB]", filepath)
            if band_match:
                band = band_match.group()
        except Exception as e:
            self.logger.exception(f"Error extracting band: {e}")
        try:
            # Version from tm_data_sources
            sources = gpm_data.get("tm_data_sources", [])
            if isinstance(sources, str):
                sources = [sources]
            version = urllib.parse.urlparse(sources[0]).query
        except Exception as e:
            self.logger.exception(f"Error extracting version: {e}")
        return band, version
