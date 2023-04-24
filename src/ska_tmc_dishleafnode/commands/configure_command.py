"""
Configure class for DishLeafNode.
"""
import json
import threading
from logging import Logger
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.enum import DishMode

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
            ra_value = json_argument["pointing"]["target"]["RA"]
            dec_value = json_argument["pointing"]["target"]["dec"]
            current_dish_mode = self.component_manager.dishMode
            command_name = f"ConfigureBand{receiver_band}"
            ret_code, message = self.call_adapter_method(
                "Dish Master", self.dish_master_adapter, command_name, argin
            )
            if current_dish_mode != DishMode.STOW and ret_code == ResultCode.OK:
                ret_code, message = self.start_dish_tracking(
                    current_dish_mode, ra_value, dec_value
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

    def start_dish_tracking(self, current_dish_mode, ra_value, dec_value):
        """Invoke Track after waiting for DishMode to Operate"""
        # Set wait for DishMode CONFIG
        ret_code, msg = self.ensure_dish_is_configured(current_dish_mode)
        if ret_code == ResultCode.FAILED:
            return ret_code, msg
        if current_dish_mode == DishMode.STANDBY_FP:
            ret_code, msg = self.ensure_dish_in_right_dish_mode()
            if ret_code == ResultCode.FAILED:
                return ret_code, msg
        # start tracking thread
        self.start_tracking_thread(ra_value, dec_value)
        return ResultCode.OK, ""

    def ensure_dish_is_configured(self, current_dish_mode):
        """This method check for the completion of configure command
        :param current_dish_mode: str
        """
        result = self.set_wait_for_dishmode(DishMode.CONFIG)
        if not result:
            self.logger.error(
                "Timeout occured while waiting for CONFIG dishMode in Configure Command."
            )
            return (
                ResultCode.FAILED,
                "Timeout occured while waiting for CONFIG dishMode in Configure Command.",
            )
        # Set wait for initial Dish Mode
        result = self.set_wait_for_dishmode(current_dish_mode)
        if not result:
            self.logger.error(
                f"""Timeout occured while waiting for
                        {current_dish_mode} dishMode in Configure Command."""
            )
            return (
                ResultCode.FAILED,
                f"""Timeout occured while waiting for
                        {current_dish_mode} dishMode in Configure Command.""",
            )
        return ResultCode.OK, ""

    def ensure_dish_in_right_dish_mode(self):
        """This method set dish to Operate Mode"""
        ret_code, message = self.call_adapter_method(
            "Dish Master", self.dish_master_adapter, "SetOperateMode"
        )

        if ret_code == ResultCode.FAILED:
            return ret_code, message

        result = self.set_wait_for_dishmode(DishMode.OPERATE)
        if not result:
            self.logger.error(
                """Timeout occured while invoking the SetOperateMode
                Command.
                """
            )
            return (
                ResultCode.FAILED,
                """Timeout occured while invoking the SetOperateMode
                Command.
                """,
            )
        return ResultCode.OK, ""

    def start_tracking_thread(self, ra_value, dec_value):
        """
        :param ra_value: Ra value
        :param dec_value: Dec value
        """
        self.component_manager.track_on_dish = False
        self.component_manager.el_limit = True
        self.component_manager.event_track_time.clear()
        self.tracking_thread = threading.Thread(
            None,
            self.component_manager.track_thread,
            "DishLeafNode",
            args=(ra_value, dec_value, self),
        )
        self.tracking_thread.start()
        self.logger.info(
            f"Track command invoked successfully with ra {ra_value} and dec {dec_value}"
        )
