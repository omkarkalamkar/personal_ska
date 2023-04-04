"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
import json

# pylint: disable=W0222
import time
from logging import Logger
from typing import Callable, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.adapters import AdapterFactory
from ska_tmc_common.device_info import DishDeviceInfo
from ska_tmc_common.enum import DishMode, LivelinessProbeType, PointingState
from ska_tmc_common.exceptions import CommandNotAllowed, DeviceUnresponsive
from ska_tmc_common.tmc_component_manager import TmcLeafNodeComponentManager

from ska_tmc_dishleafnode.commands.configure_command import Configure
from ska_tmc_dishleafnode.commands.scan_command import Scan
from ska_tmc_dishleafnode.commands.setoperatemode import SetOperateMode
from ska_tmc_dishleafnode.commands.setstandbyfpmode import SetStandbyFPMode
from ska_tmc_dishleafnode.commands.setstandbylpmode import SetStandbyLPMode
from ska_tmc_dishleafnode.commands.setstowmode import SetStowMode
from ska_tmc_dishleafnode.manager.event_receiver import DishLNEventReceiver

# pylint: disable=abstract-method


class DishLNComponentManager(TmcLeafNodeComponentManager):
    """
    A component manager for The Dish Leaf Node component.
    """

    # pylint: disable=unused-argument
    def __init__(
        self,
        dish_dev_name: str,
        logger: Logger,
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        _liveliness_probe=LivelinessProbeType.SINGLE_DEVICE,
        _event_receiver: bool = True,
        max_workers: int = 1,
        proxy_timeout: int = 500,
        sleep_time: int = 1,
        timeout: int = 2,
    ):
        """
        Initialise a new ComponentManager instance.
        :param logger: a logger for this component manager
        :param liveliness_probe: allows enabling/disabling the
        liveliness probe
        :param component_state_callback: callback to be called
        when state of the component changed
        :param communication_state_callback: callback to be called
        when communication status of the component changed
        :param event_receiver: flag used to control whether
        EventReceiver object should be instantiated or not
        :param max_workers: allows to specify number of threads
        to be used by the liveliness probe;
        :param proxy_timeout: allows to specify a client side timeou
        for sub-devices in milliseconds used by the liveliness probe;
        :param sleep_time: allows to specify the wait between
        each iteration of the liveliness probe and EventSubscriber;
        :param timeout: Time period to wait for initialization
        of adapter.
        """
        super().__init__(
            logger=logger,
            _liveliness_probe=_liveliness_probe,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            max_workers=max_workers,
            proxy_timeout=proxy_timeout,
            sleep_time=sleep_time,
        )

        self.logger = logger
        self._device = DishDeviceInfo(dish_dev_name)
        __adapter_factory = AdapterFactory()
        self.timeout = timeout
        self.dish_dev_name = dish_dev_name
        self.dish_number = None
        self.observer = None

        # Event Receiver
        if _event_receiver:
            self.event_receiver_object = DishLNEventReceiver(self, logger)
            self.event_receiver_object.start()

        self.setstandbyfpmode_command = SetStandbyFPMode(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.setstandbylpmode_command = SetStandbyLPMode(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.setstowmode_command = SetStowMode(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.setoperatemode_command = SetOperateMode(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.configure_command = Configure(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )
        self.scan_command = Scan(
            self,
            self.op_state_model,
            __adapter_factory,
            logger=self.logger,
        )

    @property
    def dishMode(self) -> DishMode:
        """Returns the dishMode of dish master device"""
        return self._device.dish_mode

    def stop_event_receiver(self) -> None:
        """Stops the Event Receiver"""
        if self.event_receiver_object._thread.is_alive():
            self.event_receiver_object.stop()

    def get_device(self) -> DishDeviceInfo:
        """
        Return the device info of the monitoring loop with name dev_name

        :param None:
        :return: a device info
        :rtype: DishDeviceInfo
        """
        return self._device

    def update_event_failure(self) -> None:
        with self.lock:
            dev_info = self.get_device()
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)

    def setstandbyfpmode(
        self, task_callback: Optional[Callable] = None
    ) -> Tuple[TaskStatus, str]:
        """
        Initializes the attributes and properties of the DishLeafNode.
        :return:
            A tuple containing a return code and a string message
            indicating status. The message is for information purpose only.
        """
        task_status, response = self.submit_task(
            self.setstandbyfpmode_command.set_standby_fp_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("SetStandbyFPMode command queued for execution")
        return task_status, response

    def setstandbylpmode(
        self, task_callback: Optional[Callable] = None
    ) -> Tuple[TaskStatus, str]:
        """Submits the SetStandbyLPMode command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.setstandbylpmode_command.set_standby_lp_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("SetStandbyLPMode command queued for execution")
        return task_status, response

    def setstowmode(
        self, task_callback: Optional[Callable] = None
    ) -> Tuple[TaskStatus, str]:
        """Submits the SetStowMode command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.setstowmode_command.set_stow_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("SetStowMode command queued for execution")
        return task_status, response

    def scan(
        self, task_callback: Optional[Callable] = None
    ) -> Tuple[TaskStatus, str]:
        """Submits the Scan command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.scan_command.scan,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("Scan command queued for execution")
        return task_status, response

    def setoperatemode(
        self, task_callback: Optional[Callable] = None
    ) -> Tuple[TaskStatus, str]:
        """Submits the SetOperateMode command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.setoperatemode_command.set_operate_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("SetOperateMode command queued for execution")
        return task_status, response

    def configure(
        self, argin: str, task_callback: Optional[Callable] = None
    ) -> tuple:
        """
        Submit the Configure command in queue.

        :return: a result code and message
        """
        try:
            input_json = json.loads(argin)
        except Exception as e:
            self.logger.exception(
                "Exception occured while loading the input json: %s", e
            )
            return (
                ResultCode.FAILED,
                f"Error while loading the input json: {e}",
            )

        # validate the JSON argument
        validation_result = self.configure_command.validate_json_argument(
            input_json
        )
        if validation_result[0] != ResultCode.OK:
            return validation_result

        # submit the command to the queue
        task_status, response = self.submit_task(
            self.configure_command.invoke_configure,
            args=[argin, self.logger],
            task_callback=task_callback,
        )
        self.logger.info("Configure command queued for execution")
        return task_status, response

    def is_configure_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.
        """

        if self.dishMode in [
            DishMode.STANDBY_FP,
            DishMode.STOW,
            DishMode.OPERATE,
            DishMode.CONFIG,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the Configure command on this"
            + "device is not allowed."
            + "Reason: The current dish mode is"
            + f"{self.dishMode}"
            + "The command has NOT been executed."
            + "This device will continue with normal operation."
        )

    def is_setstowmode_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.
        """

        if self.dishMode in [
            DishMode.STANDBY_FP,
            DishMode.OPERATE,
            DishMode.STANDBY_LP,
            DishMode.CONFIG,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the SetStowMode command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_setoperatemode_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.
        """

        if self.dishMode in [
            DishMode.STANDBY_FP,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the SetStowMode command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_setstandbyfpmode_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.
        """

        if self.dishMode in [
            DishMode.STANDBY_LP,
            DishMode.OPERATE,
            DishMode.STOW,
            DishMode.MAINTENANCE,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the SetStowMode command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_setstandbylpmode_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.
        """

        if self.dishMode in [
            DishMode.STANDBY_FP,
            DishMode.STOW,
            DishMode.MAINTENANCE,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the SetStowMode command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def is_scan_allowed(self) -> bool:
        """Checks if the given command is allowed in current operational
        state.
        """

        if self.dishMode in [
            DishMode.OPERATE,
            DishMode.STANDBY_FP,
            DishMode.STOW,
            DishMode.MAINTENANCE,
        ]:
            return True

        raise CommandNotAllowed(
            "The invocation of the Scan command on this "
            + "device is not allowed. "
            + "Reason: The current dish mode is "
            + f"{self.dishMode}. "
            + "The command has NOT been executed. "
            + "This device will continue with normal operation."
        )

    def check_device_responsive(self) -> None:
        """Checks if dish master device is responsive."""
        if self._device is None or self._device.unresponsive:
            raise DeviceUnresponsive(f"{self.dish_dev_name} not available")

    def update_device_dish_mode(self, dish_mode: DishMode) -> None:
        """
        Update the dish mode of the given dish and call
        the relative callbacks if available.
        :param dishMode: Dish mode of the device
        :type dishMode: DishMode
        """
        with self.lock:
            dev_info = self.get_device()
            dev_info.dish_mode = dish_mode
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)

    def update_device_pointing_state(
        self, pointingState: PointingState
    ) -> None:
        """
        Update the pointing state of the given dish and call
        the relative callbacks if available.
        :param pointingState: Pointing state of the dish device
        :type pointingState: PointingState
        """
        with self.lock:
            dev_info = self.get_device()
            dev_info.pointing_state = pointingState
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)

    def set_dish_name_number(self, dish_master_fqdn):
        """Find out dish number from DishMasterFQDN
        property e.g. SKA001/dish/master"""
        dish_name_string = dish_master_fqdn.split("/")[0]
        self.dish_number = dish_name_string
