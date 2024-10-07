"""
TrackLoadStaticOff command class for DishLeafNode.
"""
from __future__ import annotations

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
from ska_tmc_common import TimeoutCallback

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
    ):
        super().__init__(
            component_manager, op_state_model, adapter_factory, logger
        )
        self.task_callback = None
        self.timeout_id = None
        self.timeout_callback = None
        self.task_callback: TaskCallbackType

    # pylint: disable=unused-argument
    def invoke_track_load_static_off(
        self: TrackLoadStaticOff,
        argin: str,
        logger: Logger,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        # pylint: enable=unused-argument
        """A method to invoke the do method of the TrackLoadStaticOff command
        class. This method also updates the task callback according to command
        status.

        :param argin: Input argument containing the cross elevation and
            elevation offsets.
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
        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback = TimeoutCallback(self.timeout_id, self.logger)
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        if self.component_manager.is_configure_command is False:
            self.set_command_id(__class__.__name__)
            self.component_manager.start_timer(
                self.timeout_id,
                self.component_manager.command_timeout,
                self.timeout_callback,
            )
        else:
            logger.info(
                " TrackLoadStaticOff is invoked as part of Configure"
                + " command. The configure timer is utilised."
            )
        result_code, message = self.do(argin)
        self.component_manager.command_in_progress = "TrackLoadStaticOff"
        if result_code in [
            ResultCode.FAILED,
            ResultCode.REJECTED,
            ResultCode.NOT_ALLOWED,
        ]:
            logger.warning("Command failed with exception: %s", message)
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(result_code, message),
                exception=message,
            )
            self.component_manager.command_in_progress = ""
        else:
            logger.info(
                "The TrackLoadStaticOff command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )
            if self.component_manager.is_configure_command is False:
                logger.info(
                    "Configure flag is: %s",
                    self.component_manager.is_configure_command,
                )
                self.start_tracker_thread(
                    "get_track_load_static_off_result",
                    [ResultCode.OK],
                    task_abort_event,
                    self.timeout_id,
                    self.timeout_callback,
                    self.component_manager.command_id,
                    self.component_manager.long_running_result_callback,
                )
            else:
                logger.info(
                    " TrackLoadStaticOff is invoked as part of Configure"
                    + " command. The command status is monitored in "
                    + "Configure command tracker thread."
                )

    # pylint: disable=signature-differs
    # pylint: disable=arguments-differ
    def do(self: TrackLoadStaticOff, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke TrackLoadStaticOff command on DishMaster.

        param argin: String containing cross elevation and elevation offsets

        return:
            (ResultCode, str)
        """

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter for device : %s is not found",
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

        return result_code[0], message[0]
