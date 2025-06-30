""" This module contains GenerateProgramTrackTable implementation. """

import logging
from typing import Callable, Optional, Tuple

from ska_tango_base.commands import ResultCode, TaskStatus

from ska_dishln_pointing_device.mapping_scan.point_mapping import (
    FixedMappingScan,
)

# from ska_tango_base.commands import ResultCode, SlowCommand, TaskStatus


class GenerateProgramTrackTable:
    """Long-running version of GenerateProgramTrackTable."""

    def __init__(self, component_manager, logger: logging.Logger = None):
        super().__init__(logger)
        self.component_manager = component_manager

    def generate_program_track_table(
        self,
        *args,
        **kwargs,
    ) -> Tuple[ResultCode, str]:
        """
        This is a long running method for GenerateProgramTrackTable command,
        executes do hook, invokes command asynchronously.
        """

        task_callback: Optional[Callable] = kwargs.get("task_callback", None)

        task_callback(status=TaskStatus.IN_PROGRESS)
        return_code, message = self.do()
        self.logger.debug(
            "Updating Task status with Result: %s ,Message: %s",
            ResultCode(return_code),
            message,
        )
        if return_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(return_code, message),
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, message),
            )

    def do(self) -> Tuple[ResultCode, str]:
        """Executes the command asynchronously."""

        try:
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

        except Exception as e:
            self.logger.exception("Exception GenerateProgramTrackTable")

            return ResultCode.FAILED, str(e)

        return ResultCode.OK, "ProgramTrackTable generation completed."


# """This module contains GenerateProgramTrackTable implementation.
# """
# import logging

# from ska_tango_base.commands import FastCommand, ResultCode

# from ska_dishln_pointing_device.dishlnpd_component_manager import (
#     dishlnpd_component_manager as manager,
# )
# from ska_dishln_pointing_device.mapping_scan.point_mapping import (
#     FixedMappingScan,
# )


# class GenerateProgramTrackTable(FastCommand):
#     """This class contains GenerateProgramTrackTrable implementation"""

#     def __init__(
#         self,
#         logger: logging.Logger,
#         component_manager: manager.DishlnPointingDataComponentManager,
#     ):
#         """Initialization.

#         Args:
#             logger (logging.Logger): Used for logging.
#          component_manager (DishlnPointingDataComponentManager): Instance of
#             DishlnPointingDataComponentManager.
#         """
#         super().__init__(logger)
#         self.component_manager = component_manager

#     def do(self, *args, **kwargs) -> None:
#         """This method generates program track table."""
#         try:
#             self.logger.info(
#                 "Executing GenerateProgramTrackTable command on %s",
#                 self.component_manager.dishln_pointing_device_name,
#             )
#             with self.component_manager.track_thread_lock:
#                 self.component_manager.mapping_scan_event.clear()
#           self.component_manager.current_mapping_scan_obj = FixedMappingScan(
#                 pattern_name="fixed",
#                 component_manager=self.component_manager,
#                 logger=self.logger,
#             )
#           current_scan_obj = self.component_manager.current_mapping_scan_obj
#             current_scan_obj.set_target_and_start_process()
#         except Exception as exception:
#             self.logger.exception(
#                 " Exception occurred "
#                 + "in GenerateProgramTrackTable command on %s ,"
#                 + "Exception: %s",
#                 self.component_manager.dishln_pointing_device_name,
#                 exception,
#             )
#             raise exception
#         return ResultCode.STARTED, "ProgramTrackTable generation started"
