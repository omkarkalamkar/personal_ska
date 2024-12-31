"""
AbortCommands command class for DishLeafNode.
"""

import logging
from typing import Tuple

from ska_control_model import HealthState
from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.enum import PointingState

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE

configure_logging()
LOGGER = logging.getLogger(__name__)


class AbortCommands(DishLNCommand):
    """
    A class for DishLeafNode's AbortCommands() command.
    Command to abort the Dish Master and bring it to its ABORTED state.
    """

    def __init__(
        self,
        component_manager,
        op_state_model=None,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
    ) -> None:
        super().__init__(
            component_manager=component_manager,
            op_state_model=op_state_model,
            adapter_factory=adapter_factory,
            logger=logger,
        )
        self._name = "AbortCommands"

    # pylint: disable=unused-argument
    def invoke_abort(self, task_callback: TaskCallbackType, task_abort_event):
        """This method calls do for DishLeafNode Abort command"""
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        self.component_manager.command_in_progress = "AbortCommands"

        result_code, message = self.do()

        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(result_code, message),
                exception=message,
            )
            self.component_manager.command_in_progress = ""
        else:
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
            )
            self.logger.info(
                "The AbortCommands command invoked successfully %s",
                self.dish_master_adapter.dev_name,
            )

    # pylint: disable=arguments-differ
    def do(self) -> Tuple[ResultCode, str]:
        """
        Invokes AbortCommands command on the DishMaster.

        param argin:
            None

        return:
            A tuple containing a return code and a
            string message indicating status.
            The message is for information purpose only.

        rtype:
            (ResultCode, str)

        """
        self.logger.debug(
            "Command in progress: %s",
            self.component_manager.command_in_progress,
        )
        self.component_manager.abort_event.set()
        self.logger.debug("Abort event is set.")
        self.component_manager.observable.notify_observers(
            attribute_value_change=True
        )
        self.component_manager.abort_event.clear()
        if not self.component_manager.command_in_progress:
            self.component_manager.abort_event.clear()
            self.logger.info("Abort event is cleared")

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter for device : %s is not found.",
                self.component_manager.dish_dev_name,
            )
            return result_code, message

        self.logger.info(
            "Dish Abort commands device property is: %s",
            self.component_manager.is_dish_abort_commands_enabled,
        )

        if self.component_manager.is_dish_abort_commands_enabled:
            with self.component_manager.tango_operation_execution_lock:
                self.logger.debug("Acquired  tango lock")
                result_code, message = self.call_adapter_method(
                    "Dish Master", self.dish_master_adapter, "AbortCommands"
                )

            self.logger.debug("Released tango lock")
            self.logger.info(
                "AbortCommands() command has been invoked, the result code"
                + " is %s and the message is %s",
                result_code[0],
                message[0],
            )
            if result_code[0] in [
                ResultCode.REJECTED,
                ResultCode.NOT_ALLOWED,
                ResultCode.ABORTED,
            ]:
                return result_code[0], message[0]

        # call stop_tracking_thread to stop live thread
        result_code, message = self.stop_dish_tracking()
        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            return result_code, message

        self.component_manager.clear_track_table_errors()

        self.logger.debug(
            "AbortCommands command executed successfully on"
            + " the DishLeafNode."
        )
        return ResultCode.OK, COMMAND_COMPLETION_MESSAGE

    def stop_dish_tracking(self) -> Tuple[ResultCode, str]:
        """Method to invoke track stop when abortcommands command is invoked

        rtype:
            (ResultCode, str)
        """
        result_code, message = [ResultCode.OK], ""
        pointing_state = self.component_manager.pointingState
        # Check Pointing State is track before calling track stop.
        if pointing_state in [PointingState.TRACK, PointingState.SLEW]:
            with self.component_manager.tango_operation_execution_lock:
                result_code, msg = self.call_adapter_method(
                    "Dish Master", self.dish_master_adapter, "TrackStop"
                )
                if result_code[0] in [
                    ResultCode.FAILED,
                    ResultCode.REJECTED,
                    ResultCode.NOT_ALLOWED,
                ]:
                    message = (
                        f"TrackStop result code: {result_code[0]} "
                        + f"and message: {msg[0]}"
                    )

        try:
            self.dishln_pointing_device_adapter.StopProgramTrackTable()
        except Exception as exception:
            self.logger.exception(
                "Unable to stop programTrackTable: %s",
                exception,
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
