"""
SetStowMode command class for DishLeafNode.
"""
from __future__ import annotations

import logging
import threading

# import threading
from functools import partial
from typing import Callable, Dict, Optional, Tuple, Union

from ska_control_model import HealthState
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode, SlowCommand
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import DishMode
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_dishleafnode.commands.dish_ln_command import (
    DishLNCommand,
    task_callback_default,
)
from ska_tmc_dishleafnode.enums.stow_status import StowStatus


class StowCommand(SlowCommand):
    """A class for stow command."""

    def __init__(
        self,
        command_tracker,
        component_manager,
        callback: Callable[[bool], None] | None,
        logger: logging.Logger | None = None,
    ) -> None:
        """
        Initialise a new AbortCommand instance.

        :param command_tracker: the device's command tracker
        :param component_manager: the device's component manager
        :param callback: callback to be called when this command
            starts and finishes
        :param logger: a logger for this command object to use
        """
        self._command_tracker = command_tracker
        self._component_manager = component_manager
        super().__init__(callback=callback, logger=logger)

    def do(
        self,
        *args,
        **kwargs,
    ) -> tuple[ResultCode, str]:
        """
        Stateless hook for Abort() command functionality.

        :param args: positional arguments to the command. This
            command does not take any, so this should be empty.
        :param kwargs: keyword arguments to the command. This
            command does not take any, so this should be empty.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        command_id = self._command_tracker.new_command(
            "SetStowMode", completed_callback=self._completed
        )

        status, _ = self._component_manager.setstowmode(
            partial(self._command_tracker.update_command_info, command_id)
        )
        assert status == TaskStatus.IN_PROGRESS

        return ResultCode.STARTED, command_id


class SetStowMode(DishLNCommand):
    """
    A class for DishleafNode's SetStowMode() command.

    SetStowMode command on DishLeafNode enables the telescope to perform
    further operations and observations. It Invokes SetStowMode command on
    Dish Leaf Node device.
    """

    # pylint: disable=unused-argument
    @timeout_tracker
    @error_propagation_tracker(
        "get_dish_mode",
        [DishMode.STOW],
    )
    def invoke_set_stow_mode(
        self: SetStowMode,
        task_callback: TaskCallbackType = task_callback_default,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """A method to invoke the SetStowMode command.
        It sets the task_callback status according to command progress.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType, optional
        """
        return self.do()

    # pylint: enable=unused-argument

    def update_task_status(
        self,
        **kwargs: Dict[str, Union[Tuple[ResultCode, str], TaskStatus, str]],
    ) -> None:
        """
        Update the status of a task.

        Args:
            **kwargs: Keyword arguments for task status update.
        """
        result = kwargs.get("result")
        status = kwargs.get("status", TaskStatus.COMPLETED)
        message = kwargs.get("exception")
        self.logger.debug(
            "Task result: %s, Status: %s, Message: %s",
            result,
            status,
            message,
        )
        if status == TaskStatus.ABORTED:
            self.task_callback(status=status)
        if result:
            if result[0] == ResultCode.FAILED:
                self.task_callback(
                    status=status, result=result, exception=message
                )
                if (
                    self.component_manager.stow_status
                    == StowStatus.MANUAL_STOW_STARTED
                ):
                    self.component_manager.stow_status = (
                        StowStatus.MANUAL_STOW_FAILED
                    )
            else:
                self.task_callback(status=status, result=result)
                if (
                    self.component_manager.stow_status
                    == StowStatus.MANUAL_STOW_STARTED
                ):
                    self.component_manager.stow_status = (
                        StowStatus.MANUAL_STOW_COMPLETED
                    )
        self.component_manager.command_in_progress = ""
        if not self.component_manager.is_configure_command:
            self.component_manager.clear_configure_command_events_flags()

    # pylint: disable-next=arguments-differ
    def do(self: SetStowMode) -> Tuple[ResultCode, str]:
        """
        Method to invoke SetStowMode command on DishMaster.

        Returns:
            Tuple[ResultCode, str]: Tuple of ResultCode and message.

        """

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.debug(
                "Command ID: %s | Adapter for : %s is not found ",
                self.component_manager.command_id,
                self.component_manager.dish_dev_name,
            )
            return result_code, message
        with self.component_manager.tango_operation_execution_lock:
            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "SetStowMode"
            )
        if result_code[0] == ResultCode.FAILED:
            return result_code[0], message[0]

        result_code, message = self.stop_program_track_table()

        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            return result_code, message

        self.component_manager.clear_track_table_errors()
        self.component_manager.abort_event.clear()
        return ResultCode.OK, "Command Invocation Completed"

    def stop_program_track_table(self) -> Tuple[ResultCode, str]:
        """Method to invoke StopProgramTrackTable() when abort command is
        invoked.

        Returns:
            Tuple[ResultCode, str]: Tuple of ResultCode and message.
        """
        result_code, message = [ResultCode.OK], ""

        try:
            self.dishln_pointing_device_adapter.StopProgramTrackTable()
        except Exception as exception:
            self.logger.exception(
                "Unable to stop programTrackTable: %s",
                str(exception),
            )
            self.component_manager.current_track_table_error = (
                f"Exception while stopping programTrackTable {exception}"
            )
            if self.component_manager._update_health_state_callback:
                self.component_manager._update_health_state_callback(
                    HealthState.DEGRADED
                )
                result_code = [ResultCode.FAILED]
                message += (
                    " StopProgramTrackTable: There was an error while"
                    + " stopping the generation of "
                    + f"program track table: {exception}"
                )
        return result_code[0], message
