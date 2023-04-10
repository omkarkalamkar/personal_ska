"""
Abort command class for DishLeafNode.
"""
import threading
from logging import Logger
from typing import Callable, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.adapters import AdapterFactory

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class Abort(DishLNCommand):
    """
    A class for DishLeafNode's Abort() command.
    Command to abort the Dish Master and bring it to its ABORTED state.
    """

    def __init__(
        self,
        component_manager,
        op_state_model,
        adapter_factory: AdapterFactory,
        logger: Logger,
    ) -> None:
        super().__init__(
            component_manager,
            op_state_model,
            adapter_factory,
            logger=logger,
        )

    # pylint: disable=unused-argument
    def invoke_abort_commands(
        self,
        logger: Logger,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:

        """This is a  method for Abort command, it
        executes the do hook, invoking AbortCommands command on Dish Master

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)
        return_code, message = self.do()
        logger.info(message)
        if return_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=return_code,
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=return_code,
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

        raises:
           Raises exception if fails to execute
           TrackStop command on DishMaster.

        """
        try:
            ret_code, message = self.init_adapter()

            if ret_code == ResultCode.FAILED:
                return ret_code, message

            result_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, "AbortCommands"
            )
            self.logger.info("Abort command executed successfully.")

        except Exception as e:
            self.logger.exception(f"Command invocation failed: {e}")
            return self.generate_command_result(
                ResultCode.FAILED,
                f"""The invocation of the Abort command is failed
                on Dish Master Device {self.dish_master_adapter.dev_name}.
                Reason: Error in executing the Abort command on
                Dish Master: {self.component_manager.dish_dev_name}
                The command has NOT been executed.
                This device will continue with its current operation. {e}"""
            )
        return (result_code, message)
