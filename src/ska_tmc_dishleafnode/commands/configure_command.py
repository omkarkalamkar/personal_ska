"""
Configure class for DishLeafNode.
"""

import json
import threading
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class Configure(DishLNCommand):
    """
    A class for DishLeafNode's Configure() command.

    Configures the Dish by setting pointing coordinates
    for a given scan.
    This function accepts the input json and calculate
    pointing parameters of Dish- Azimuth
    and Elevation Angle. Calculated parameters are again
    converted to json and fed to the
    dish master.

    """

    # pylint: disable=unused-argument
    def configure(
        self,
        argin: str,
        logger,
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
        ret_code, message = self.do(json.dumps(argin))
        self.logger.info(message)
        if ret_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode.FAILED,
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode.OK,
            )

    # pylint: enable=unused-argument
    def do(self, argin: str = None) -> None:
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
            self._configure_band(receiver_band)

        except Exception as e:
            self.logger.exception(f"Command invocation failed: {e}")
            return self.generate_command_result(
                ResultCode.FAILED,
                f"""The invocation of the Configure command is failed
                on Dish Master Device {self.dish_master_adapter.dev_name}.
                Reason: Error in calling the Configure command on
                Dish Master.
                The command has NOT been executed.
                This device will continue with normal operation.""",
            )
        return (ResultCode.OK, "")

    def _configure_band(self, band):
        """ "Send the ConfigureBand<band-number> command to Dish Master"""
        command_name = f"ConfigureBand{band}"

        ret_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, command_name
        )
        return ret_code, message
