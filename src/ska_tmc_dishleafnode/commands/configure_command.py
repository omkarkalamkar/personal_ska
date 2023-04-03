"""
Configure class for DishLeafNode.
"""
import json
import threading
from logging import Logger
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class Configure(DishLNCommand):
    """
    A class for DishLeafNode's Configure command.

    Configures the Dish by setting pointing coordinates
    for a given scan.
    This function accepts the input json and calculate
    pointing parameters of Dish- Azimuth
    and Elevation Angle. Calculated parameters are again
    converted to json and fed to the
    dish master.

    """

    # pylint: disable=unused-argument
    def invoke_configure(
        self,
        argin: str,
        logger: Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:

        """This is a long running method for Configure command, it
        executes do hook, invokes Configure command on Dish Master.

        :param argin: Input JSON string
        :type argin : str
        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)
        return_code, message = self.do(argin)
        logger.info(message)
        if return_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=return_code,
                exception=message,
            )
        else:
            logger.info(
                "The Configure command is invoked successfully on %s",
                self.dish_master_adapter.dev_name,
            )
            task_callback(
                status=TaskStatus.COMPLETED,
                result=return_code,
            )

    # pylint: enable=unused-argument

    def validate_json_argument(self, input_argin: dict) -> tuple:
        """Validates the json argument"""

        if "pointing" not in input_argin:
            return self.generate_command_result(
                ResultCode.FAILED,
                "pointing key is not present in the input json argument.",
            )
        if "dish" not in input_argin:
            return self.generate_command_result(
                ResultCode.FAILED,
                "dish key is not present in the input json argument.",
            )

        if "receiverBand" not in input_argin["dish"]:
            return self.generate_command_result(
                ResultCode.FAILED,
                "receiverBand key is not present in the input json argument.",
            )

        return (ResultCode.OK, "")

    def do(self, argin: str = None):
        """
        Method to invoke Configure command on dish.

        :param argin:
            A String in a JSON format that includes pointing parameters
            of Dish- Azimuth and
            Elevation Angle.

                Example:
                {"pointing":{"target":{"system":"ICRS",
                "name":"Polaris Australis",
                "RA":"21:08:47.92",
                "dec":"-88:57:22.9"}},
                "dish":{"receiverBand":"1"}}

        return:
            None

        raises:
            DevFailed If error occurs while invoking ConfigureBand<> command
            on DishMaster or
            if the json string contains invalid data.

        """
        try:
            ret_code, message = self.init_adapter()
            if ret_code == ResultCode.FAILED:
                return ret_code, message

            json_argument = json.loads(argin)
            receiver_band = json_argument["dish"]["receiverBand"]
            command_name = f"ConfigureBand{receiver_band}"
            ret_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, command_name, argin
            )

        except Exception as e:
            self.logger.exception(f"Command invocation failed: {e}")
            return self.generate_command_result(
                ResultCode.FAILED,
                f"""The invocation of the Configure command is failed
                on Dish Master Device {self.dish_master_adapter.dev_name}.
                Reason: Error in calling the Configure command on
                Dish Master: {e}
                The command has NOT been executed.
                This device will continue with normal operation.""",
            )
        return ret_code, message
