"""This module provides base command class for DishLeafNode."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Callable, Dict, Optional, Tuple, Union

from ska_control_model import TaskStatus
from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tmc_common import (
    AdapterFactory,
    AdapterType,
    DishMode,
    TimeKeeper,
    TimeoutCallback,
    TimeoutState,
    TmcLeafNodeCommand,
)
from ska_tmc_common.command_completion_tracker import (
    CommandCompletionContext,
    CommandCompletionTracker,
)
from tango import ConnectionFailed, DevFailed

configure_logging()
LOGGER = logging.getLogger(__name__)
if TYPE_CHECKING:
    from ..manager.component_manager import DishLNComponentManager


def task_callback_default(
    **kwargs,
) -> None:
    """
    Default method if the taskcallback is not passed

    :param status: status of the task.
    :param progress: progress of the task.
    :param result: result of the task.
    :param exception: an exception raised from the task.
    """
    result = kwargs.get("result", None)
    status = kwargs.get("status", TaskStatus.COMPLETED)
    message = kwargs.get("message") or kwargs.get("exception", None)
    progress = kwargs.get("progress") or kwargs.get("exception", None)

    LOGGER.warning(
        "This is default task callback."
        + "There is no action taken under this callback."
        + "Please provide task callback."
    )
    LOGGER.info(
        "Long running command status: %s, Progress: %s ,Result:%s ,"
        + "Exception %s",
        status,
        progress,
        result,
        message,
    )


class DishLNCommand(TmcLeafNodeCommand):
    """A base command class for DishLeafNode with the methods and parameters
    common across all the commands."""

    def __init__(
        self: DishLNCommand,
        component_manager: DishLNComponentManager,
        op_state_model,
        adapter_factory=None,
        logger: logging.Logger = LOGGER,
        add_to_command_in_progress_list: bool = True,
    ):
        super().__init__(component_manager, logger)
        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback: Callable[
            [str, TimeoutState], Optional[ValueError]
        ] = TimeoutCallback(self.timeout_id, self.logger)
        self.task_callback: Callable
        self.op_state_model = op_state_model
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.dish_master_adapter = None
        self.dishln_pointing_device_adapter = None
        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, logger
        )
        self.command_uniq_id: str = ""
        self.is_aborted: bool = False
        if add_to_command_in_progress_list:
            self.component_manager.command_in_progress_objects.append(self)

    def init_adapter(self: DishLNCommand):
        """Creates adapter for underlying Dish device."""
        dev_name = self.component_manager.dish_dev_name
        adapter_timeout = self.component_manager.adapter_timeout
        elapsed_time = 0
        start_time = time.time()
        while (
            self.dish_master_adapter is None
            and elapsed_time <= adapter_timeout
        ):
            try:
                self.dish_master_adapter = (
                    self._adapter_factory.get_or_create_adapter(
                        dev_name, AdapterType.DISH
                    )
                )
                self.dish_master_adapter.proxy.set_timeout_millis(5000)
                self.logger.debug(
                    "Dish Manager adapter created successfully",
                )
                self.component_manager.set_dish_adapter(
                    self.dish_master_adapter
                )
            except ConnectionFailed as connection_failed:
                elapsed_time = time.time() - start_time
                if elapsed_time > adapter_timeout:
                    return (
                        ResultCode.FAILED,
                        "Error in creating adapter for "
                        f"{dev_name}: {connection_failed}",
                    )
            except DevFailed as device_failed:
                elapsed_time = time.time() - start_time
                if elapsed_time > adapter_timeout:
                    return (
                        ResultCode.FAILED,
                        f"Error in creating adapter for "
                        f"{dev_name}: {device_failed}",
                    )

            except (AttributeError, ValueError, TypeError) as exception:
                return (
                    ResultCode.FAILED,
                    f"Error in creating adapter for "
                    f"{dev_name}: {exception}",
                )

        elapsed_time = 0
        start_time = time.time()
        dev_name = self.component_manager.dishln_pointing_dev_name
        while (
            self.dishln_pointing_device_adapter is None
            and elapsed_time <= adapter_timeout
        ):
            try:
                self.dishln_pointing_device_adapter = (
                    self._adapter_factory.get_or_create_adapter(
                        dev_name,
                        AdapterType.DISHLN_POINTING_DEVICE,
                    )
                )
                self.dishln_pointing_device_adapter.proxy.set_timeout_millis(
                    5000
                )
                self.logger.debug(
                    "Adapter for Dishleafnode pointing device"
                    + " created successfully",
                )
                self.component_manager.set_dishln_pointing_device_adapter(
                    self.dishln_pointing_device_adapter
                )
            except ConnectionFailed as connection_failed:
                elapsed_time = time.time() - start_time
                if elapsed_time > adapter_timeout:
                    return (
                        ResultCode.FAILED,
                        f"Error in creating adapter for "
                        f"{dev_name}: {connection_failed}",
                    )
            except DevFailed as device_failed:
                elapsed_time = time.time() - start_time
                if elapsed_time > adapter_timeout:
                    return (
                        ResultCode.FAILED,
                        f"Error in creating adapter for "
                        f"{dev_name}: {device_failed}",
                    )

            except (AttributeError, ValueError, TypeError) as exception:
                return (
                    ResultCode.FAILED,
                    f"Error in creating adapter for "
                    f"{dev_name}: {exception}",
                )

        return ResultCode.OK, "Adapter initialisation is successful"

    def set_wait_for_dishmode(self: DishLNCommand, dishmode: DishMode) -> str:
        """Waits for transition of DishMode to the correct state.

        Args:
            dishmode (DishMode): DishMode value to wait for.

        Returns:
            str: `ACHIEVED` if the DishMode transitions to the correct state
            within the timeout period,
            `NOT_ACHIEVED` if it doest not transition within
            timeout or `ABORTED` if abort cammand is called while execution.

        """
        start_time = time.time()
        elapsed_time = 0
        flag = "NOT_ACHIEVED"
        while elapsed_time < self.component_manager.command_timeout:
            if self.component_manager.abort_event.is_set():
                flag = "ABORTED"
                return flag
            if self.component_manager.dishMode == dishmode:
                flag = "ACHIEVED"
                return flag
            elapsed_time = time.time() - start_time

        self.logger.info("Dish mode is %s", self.component_manager.dishMode)
        return flag

    def init_adapter_mid(self: DishLNCommand):
        self.init_adapter()

    def set_command_id(self, command_name: str):
        """
        Sets the command id for error propagation.

        :param command_name: Name of the command
        :type command_name: str
        """
        command_id = f"{time.time()}-{command_name}"
        self.component_manager.command_id = command_id

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
            else:
                self.task_callback(status=status, result=result)
        self.component_manager.command_in_progress = ""
        self.component_manager.remove_command_in_progress_object(self)
        if not self.component_manager.is_configure_command:
            self.component_manager.clear_configure_command_events_flags()

    def is_abort_flag_set(self) -> bool:
        """Check if the abort flag is set.

        Returns:
            bool: True if the abort flag is set, False otherwise.
        """
        return self.abort_flag

    def wait_for_completion(
        self,
        state_getter: Callable[[], bool] = None,
        desired_state: bool = True,
        device_length: int = 1,
        check_abort: bool = True,
    ) -> Tuple[ResultCode, str]:
        """Wait for command completion using CommandCompletionTracker
        Args:
            state_getter (Callable[[], bool]): Function to get the
            current state
            desired_state (ObsState): Expected observation state after
            command execution
            device_length (int): Number of devices to wait for completion
            (default is 1)
            check_abort (bool): Whether to check for abort signal
        Returns:
            Tuple[ResultCode, str]: Final result code and corresponding message
        """
        tracker = CommandCompletionTracker(self.logger)

        context = CommandCompletionContext(
            command_results=self.command_results,
            completion_condition=(
                self.component_manager.command_completion_cond
            ),
            timeout=self.component_manager.command_timeout,
            device_length=device_length,
            check_abort=check_abort,
            state_getter=state_getter,
            desired_state=desired_state,
            abort_checker=self.is_abort_flag_set,
        )

        return tracker.wait_for_command_completion(context)
