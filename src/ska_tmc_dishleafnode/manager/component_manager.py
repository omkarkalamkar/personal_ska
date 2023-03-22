"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
# pylint: disable=W0222
from typing import Callable, Optional, Tuple

from ska_tango_base.executor import TaskStatus
from ska_tmc_common.adapters import AdapterFactory
from ska_tmc_common.device_info import DishDeviceInfo
from ska_tmc_common.enum import DishMode, LivelinessProbeType
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.tmc_component_manager import TmcLeafNodeComponentManager
from tango import DevState

from ska_tmc_dishleafnode.commands.configure_command import Configure
from ska_tmc_dishleafnode.commands.setoperatemode import SetOperateMode
from ska_tmc_dishleafnode.commands.setstandbyfpmode import SetStandbyFPMode
from ska_tmc_dishleafnode.commands.setstandbylpmode import SetStandbyLPMode
from ska_tmc_dishleafnode.commands.setstowmode import SetStowMode

# pylint: disable=abstract-method
# from tango import DevState


class DishLNComponentManager(TmcLeafNodeComponentManager):
    """
    A component manager for The Dish Leaf Node component.
    """

    # pylint: disable=unused-argument
    def __init__(
        self,
        dish_dev_name,
        logger=None,
        communication_state_callback=None,
        component_state_callback=None,
        _liveliness_probe=LivelinessProbeType.SINGLE_DEVICE,
        _event_receiver=False,
        max_workers=1,
        proxy_timeout=500,
        sleep_time=1,
        timeout=2,
    ):
        """
        Initialise a new ComponentManager instance.

        :param logger: a logger for this component manager
        :param liveliness_probe: allows enabling/disabling the
        liveliness probe;
        :param component_state_callback: callback to be called
         when state of the component changed
        :param communication_state_callback: callback to be called
         when communication status of the component changed
        :param event_receiver: allows eanabling/disabling the
         event subscriber;
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
            logger,
            _liveliness_probe,
            _event_receiver,
            communication_state_callback,
            component_state_callback,
            max_workers,
            proxy_timeout,
            sleep_time,
        )
        self.logger = logger
        self._device = DishDeviceInfo(dish_dev_name)
        __adapter_factory = AdapterFactory()
        self.timeout = timeout
        self.dish_dev_name = dish_dev_name
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

    @property
    def dishMode(self) -> DishMode:
        """Returns the dishMode of dish master device"""
        return self._device.dishMode

    @dishMode.setter
    def dishMode(self, value: DishMode) -> None:
        """Sets the value of Dish Mode for Dish Master Device"""
        if self._device.dishMode != value:
            self._device.dishMode = value

    def setstandbyfpmode(self, task_callback=None) -> Tuple[TaskStatus, str]:
        """Submits the SetStandbyFPMode command for execution.

        :rtype: Tuple
        """
        task_status, response = self.submit_task(
            self.setstandbyfpmode_command.set_standby_fp_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        self.logger.info("SetStandbyFPMode command queued for execution")
        return task_status, response

    def setstandbylpmode(self, task_callback=None) -> Tuple[TaskStatus, str]:
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

    def setstowmode(self, task_callback=None) -> Tuple[TaskStatus, str]:
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

    def setoperatemode(self, task_callback=None) -> Tuple[TaskStatus, str]:
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
        task_status, response = self.submit_task(
            self.configure_command.configure,
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

    def is_command_allowed(self, command_name: str) -> bool:
        """Checks if the given command is allowed in current operational
        state.
        """

        if command_name in [
            "SetStandbyFPMode",
            "SetStandbyLPMode",
            "SetStowMode",
            "SetOperateMode",
        ]:
            if self.op_state_model.op_state in [
                DevState.FAULT,
                DevState.UNKNOWN,
                DevState.DISABLE,
            ]:
                raise CommandNotAllowed(
                    "The invocation of the {} command on this".format(
                        command_name
                    )
                    + "device is not allowed."
                    + "Reason: The current operational state is"
                    + "{}".format(self.op_state_model.op_state)
                    + "The command has NOT been executed."
                    + "This device will continue with normal operation."
                )
            return True
        return False
