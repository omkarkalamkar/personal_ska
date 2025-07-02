""" This module contains GenerateProgramTrackTable implementation. """

import logging
from typing import Tuple

from ska_tango_base.commands import ResultCode, TaskStatus

from ska_dishln_pointing_device.mapping_scan.point_mapping import (
    FixedMappingScan,
)


class GenerateProgramTrackTable:
    """Long-running version of GenerateProgramTrackTable."""

    def __init__(self, component_manager, logger):
        self.logger: logging.Logger = logger
        self.component_manager = component_manager

    def generate_program_track_table(
        self,
        **kwargs,
    ) -> Tuple[ResultCode, str]:
        """
        This is a long running method for GenerateProgramTrackTable command,
        executes do hook, invokes command asynchronously.
        """
        task_callback = kwargs.get("task_callback")

        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            return_code, message = self.do()
        except Exception as ex:
            self.logger.exception(
                "Exception occurred in GenerateProgramTrackTable on %s: %s",
                self.component_manager.dishln_pointing_device_name,
                ex,
            )
            if task_callback:
                task_callback(
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

        if task_callback:
            task_callback(
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
