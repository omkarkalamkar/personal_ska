"""
TrackLoadStaticOff command class for DishLeafNode.
"""
import threading
from logging import Logger
from typing import Callable, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.dish_ln_command import DishLNCommand


class TrackLoadStaticOff(DishLNCommand):
    """
    A class for DishLeafNode's TrackLoadStaticOff() command.

    This command is invoked as a part of the Configure sequence of a 5 point
    calibration scan. It is used to set the cross elevation and elevation
    offsets provided in the partial configurations on the Dish Master Device.
    """

    # pylint: disable=unused-argument
    def invoke_track_load_static_off(
        self,
        argin: str,
        logger: Logger,
        task_callback: Callable,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        # pylint: enable=unused-argument
        """A method to invoke the TrackLoadStaticOff command.
        It sets the task_callback status according to command progress.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """

        task_callback(status=TaskStatus.IN_PROGRESS)

        result_code, message = self.do(argin)
        if result_code == ResultCode.FAILED:
            logger.warning("Command failed with exception: %s", message)
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(result_code),
                exception=message,
            )
        else:
            logger.info(
                "The TrackLoadStaticOff command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode(result_code),
            )

    # pylint: disable=signature-differs
    def do(self, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke TrackLoadStaticOff command on DishMaster.

        param argin: String containing cross elevation and elevation offsets

        return:
            (ResultCode, str)
        """

        result_code, message = self.init_adapter()
        if result_code == ResultCode.FAILED:
            self.logger.info("%s adapter not found", self.component_manager.dish_dev_name)
            return result_code, message

        result_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "TrackLoadStaticOff", argin=argin
        )

        return result_code[0], message[0]
