""" This module contains GenerateProgramTrackTable implementation. """

import logging
import threading
from typing import Any, Optional, Tuple

from ska_control_model import TaskStatus
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode

from ska_dishln_pointing_device.mapping_scan.point_mapping import (
    FixedMappingScan,
)


# pylint: disable=unused-argument
def task_callback_default(
    status: Optional[TaskStatus] = None,
    progress: Optional[int] = None,
    result: Any = None,
    exception: Optional[Exception] = None,
) -> None:
    # pylint: enable=unused-argument
    """
    Default method if the taskcallback is not passed

    :param status: status of the task.
    :param progress: progress of the task.
    :param result: result of the task.
    :param exception: an exception raised from the task.
    """


class GenerateProgramTrackTable:
    """Long-running version of GenerateProgramTrackTable."""

    def __init__(self, component_manager, logger):
        self.logger: logging.Logger = logger
        self.component_manager = component_manager
        self.task_callback: TaskCallbackType = task_callback_default

    # pylint: disable=unused-argument
    def generate_program_track_table(
        self,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> Tuple[ResultCode, str]:
        # pylint: enable=unused-argument
        """
        This is a long running method for GenerateProgramTrackTable command,
        executes do hook, invokes command asynchronously.
        """
        self.task_callback = task_callback
        self.task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            return_code, message = self.do()
        except Exception as ex:
            self.logger.exception(
                "Exception occurred in GenerateProgramTrackTable on %s: %s",
                self.component_manager.dishln_pointing_device_name,
                ex,
            )
            self.task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, str(ex)),
                exception=ex,
            )
            return ResultCode.FAILED, str(ex)

        self.logger.debug(
            "Updating Task status with Result: %s , Message: %s",
            return_code,
            message,
        )

        self.task_callback(
            status=TaskStatus.COMPLETED,
            result=(ResultCode.OK, message),
        )

        return ResultCode.OK, message

    def do(self) -> Tuple[ResultCode, str]:
        """
        Executes the GenerateProgramTrackTable command logic.
        """
        self.logger.info(
            "Executing GenerateProgramTrackTable command on %s",
            self.component_manager.dishln_pointing_device_name,
        )

        try:
            with self.component_manager.track_thread_lock:
                self.component_manager.mapping_scan_event.clear()

            self.component_manager.current_mapping_scan_obj = FixedMappingScan(
                pattern_name="fixed",
                component_manager=self.component_manager,
                logger=self.logger,
            )

            current_scan_obj = self.component_manager.current_mapping_scan_obj
            current_scan_obj.set_target_and_start_process()

            return ResultCode.OK, "Command Completed"

        except Exception as exception:
            self.logger.error(
                "Error in GenerateProgramTrackTable: %s", str(exception)
            )

            self.component_manager._current_track_table_error = str(exception)
            return ResultCode.FAILED, str(exception)
