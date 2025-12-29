"""
TrackLoadStaticOff command class for DishLeafNode.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Tuple, Union

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand

configure_logging()
LOGGER = logging.getLogger(__name__)


class TrackLoadStaticOff(DishLNCommand):
    """
    A class for DishLeafNode's TrackLoadStaticOff() command.

    This command is invoked as a part of the Configure sequence of a 5 point
    calibration scan. It is used to set the cross elevation and elevation
    offsets provided in the partial configurations on the Dish Master Device.
    """

    def __init__(
        self: TrackLoadStaticOff,
        component_manager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
        is_configure_command: bool = False,
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.is_configure_command = is_configure_command

    def update_task_status(
        self,
        **kwargs: Dict[str, Union[Tuple[ResultCode, str], TaskStatus, str]],
    ) -> None:
        """
        Update the status of a task.

        Args:
            **kwargs: Keyword arguments for task status update.
        """
        super().update_task_status(**kwargs)
        if self.component_manager.command_unique_id_dict.get(
            self.command_uniq_id
        ):
            del self.component_manager.command_unique_id_dict[
                self.command_uniq_id
            ]
            self.command_uniq_id = ""

    # pylint: disable=unused-argument
    @timeout_tracker
    @error_propagation_tracker(
        "get_track_load_static_off_result_code", [ResultCode.OK]
    )
    def invoke_track_load_static_off(
        self: TrackLoadStaticOff,
        argin: str,
    ) -> Tuple[ResultCode, str]:
        # pylint: enable=unused-argument
        """A method to invoke the do method of the TrackLoadStaticOff command
        class. This method also updates the task callback according to command
        status.

        :param argin: Input argument containing the cross elevation and
            elevation offsets.
        :type argin: str
        :return: : (ResultCode, str)
        :rtype: Tuple
        """
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        if self.is_configure_command is False:
            self.set_command_id(__class__.__name__)
        else:
            self.component_manager.command_in_progress = "Configure"

        return self.do(argin)

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self: TrackLoadStaticOff, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke TrackLoadStaticOff command on DishMaster.

        Args:
            argin (str): String containing cross elevation
                and elevation offsets.

        Returns:
            Tuple[ResultCode, str]: Tuple of ResultCode and message.
        """

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.debug(
                "Command ID: %s | Adapter for : %s is not found",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        offsets = json.loads(argin)
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master",
                self.dish_master_adapter,
                "TrackLoadStaticOff",
                argin=offsets,
            )
            if ResultCode(result_code[0]) is ResultCode.QUEUED:
                # Append command unique id
                self.component_manager.command_unique_id_dict[
                    "TrackLoadStaticOff"
                ] = message[0]
                self.command_uniq_id = message[0]
            self.logger.info(
                "Command ID: %s | "
                + "TrackLoadStaticOff command "
                + "executed on %s with ResultCode: %s,"
                + " Message: %s",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
                ResultCode(result_code[0]),
                message,
            )
        return result_code[0], message[0]
