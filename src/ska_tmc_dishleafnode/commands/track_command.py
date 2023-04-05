"""Scan command class for Dishleafnode."""

import datetime
import threading
import time
from datetime import timezone
from logging import Logger
from typing import Callable, Optional

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from tango import DevFailed

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.commands.abstract_command import DishLNCommand


class Track(DishLNCommand):
    """
    A class for Dishleafnode's Track command. Track command is
    inherited from DishLNCommand.

    This command invokes Track command on Dish Master
    """

    # pylint: disable=unused-argument
    def track(
        self,
        argin: str,
        logger: Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:

        """This is a long running method for Track command, it
        executes the do hook, invoking Track command on Dish Master

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
            task_callback(
                status=TaskStatus.COMPLETED,
                result=return_code,
            )

    def validate_json_argument(self, input_argin: dict) -> tuple:
        """Validates the json argument"""
        target = input_argin.get("pointing", {}).get("target", {})
        ra_value = target.get("ra")
        if not ra_value:
            return self.generate_command_result(
                ResultCode.FAILED,
                "ra value key is not present in the input json.",
            )

        dec_value = target.get("dec")
        if not dec_value:
            return self.generate_command_result(
                ResultCode.FAILED,
                "dec value key is not present in the input json.",
            )

        return (ResultCode.OK, "")

    def do(self, argin=None):
        """
        Method to invoke Track command on Dish Master.

        param argin:
            None

        return:
            (ResultCode, str)
        """
        return_code, message = self.init_adapter()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.ra_value = argin["pointing"]["target"]["ra"]
        self.dec_value = argin["pointing"]["target"]["dec"]
        self.component_manager.event_track_time.clear()
        try:
            # Start pointing calculations in a Track Thread
            self.tracking_thread = threading.Thread(
                None, self.track_thread, "DishLeafNode"
            )
            self.tracking_thread.start()
            radec_value = f"{self.ra_value}, {self.dec_value}"
            self.logger.info(
                "Track command ignores RA dec coordinates passed in: %s. "
                "Uses coordinates from Configure command instead.",
                radec_value,
            )
        except DevFailed as dev_failed:
            self.logger.exception(dev_failed)
            log_message = (
                "Exception occured while executing the Track command."
            )
            tango.Except.re_throw_exception(
                dev_failed,
                "Exception in Track command.",
                log_message,
                "DishLeafNode.Track Command",
                tango.ErrSeverity.ERR,
            )
        return return_code, message

    def track_thread(self):
        """This thread writes coordinates to desiredPointing
        on DishMaster at the rate of 20 Hz.
        """
        self.logger.info(
            f"print track_thread thread name:{threading.current_thread().name}"
            f"{threading.get_ident()}"
        )
        azel_converter = AzElConverter(self.component_manager)
        azel_converter.create_antenna_obj()

        while self.component_manager.event_track_time.is_set() is False:
            now = datetime.datetime.utcnow()
            timestamp = str(now)
            utc_time = now.replace(tzinfo=timezone.utc)
            utc_timestamp = utc_time.timestamp()
            # pylint: disable=unbalanced-tuple-unpacking
            az_value, el_value = azel_converter.point(
                self.ra_value, self.dec_value, timestamp
            )

            if not self._is_elevation_within_mechanical_limits(el_value):
                time.sleep(0.05)
                continue

            if az_value < 0:
                az_value = 360 - abs(az_value)

            if self.component_manager.event_track_time.is_set():
                log_message = (
                    "Break loop: "
                    f"{self.component_manager.event_track_time.is_set()}"
                )
                self.logger.debug(log_message)
                break

            # TODO (kmadisa 11-12-2020) Add a pointing lead time to
            #  the current time (like we do on MeerKAT)
            # utc_timestamp is the time used for AzEl calculation.
            # For the timestamp to be a future timestamp
            # on DishMaster, 100 ms are added to it.
            desired_pointing = [
                (utc_timestamp * 1000) + 100,
                round(az_value, 12),
                round(el_value, 12),
            ]
            self.logger.info(
                "desiredPointing coordinates: %s", desired_pointing
            )
            self.dish_master_adapter.desiredPointing = desired_pointing

            self.logger.info("Observer: %s", self.component_manager.observer)

            if self.track_on_dish is False:
                self.call_adapter_method(
                    "Dish Master", self.dish_master_adapter, "Track"
                )
                self.track_on_dish = True

            time.sleep(0.05)

    def _is_elevation_within_mechanical_limits(self, el_value):

        if not (
            self.component_manager.ele_min_lim
            <= el_value
            <= self.component_manager.ele_max_lim
        ):
            self.component_manager.el_limit = True
            log_message = "Minimum/maximum elevation limit has been reached."
            self.logger.info(log_message)
            log_message = "Source is not visible currently."
            self.logger.info(log_message)
            return False

        self.component_manager.el_limit = False
        return True
