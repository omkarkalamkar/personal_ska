"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
from ska_tmc_common.device_info import DishDeviceInfo
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.liveliness_probe import SingleDeviceLivelinessProbe
from ska_tmc_common.tmc_component_manager import TmcLeafNodeComponentManager

# pylint: disable=abstract-method
from tango import DevState

from ska_tmc_dishleafnode.commands.setstandbyfpmode_command import (
    SetStandbyFPMode,
)
from ska_tmc_dishleafnode.commands.setstandbylpmode_command import (
    SetStandbyLPMode,
)


class DishLNComponentManager(TmcLeafNodeComponentManager):
    """
    A component manager for The Dish Leaf Node component.
    """

    # pylint: disable=unused-argument,line-too-long
    def __init__(
        self,
        dish_dev_name,
        op_state_model,
        logger=None,
        communication_state_callback=None,
        component_state_callback=None,
        update_command_in_progress_callback=None,
        liveliness_probe=True,
        event_receiver=False,
        max_workers=5,
        proxy_timeout=500,
        sleep_time=1,
        timeout=30,
    ):
        """
        Initialise a new ComponentManager instance.

        :param op_state_model: the op state model used by this component
            manager
        :param logger: a logger for this component manager
        :param liveliness_probe: allows enabling/disabling the
            liveliness probe;
        :param event_receiver: allows eanabling/disabling the event subscriber;
        :param max_workers: allows to specify number of threads to be used by
        the liveliness probe;
        :param proxy_timeout: allows to specify a client side timeout for
        sub-devices in milliseconds used by the liveliness probe;
        :param sleep_time: allows to specify the wait between each iteration
        of the liveliness probe and EventSubscriber;
        """
        super().__init__(
            op_state_model,
            logger,
            liveliness_probe,
            event_receiver,
            communication_state_callback,
            component_state_callback,
            max_workers,
            proxy_timeout,
            sleep_time,
        )
        self.logger = logger
        self._device = DishDeviceInfo(dish_dev_name)

        self._liveliness_probe = None
        if liveliness_probe:
            self._liveliness_probe = SingleDeviceLivelinessProbe(
                self, self._device, logger, proxy_timeout, sleep_time
            )
            self._liveliness_probe.start()
        else:
            logger.warning("Liveliness probe is not running")

        self.timeout = timeout
        self.dish_dev_name = dish_dev_name

    def setstandbyfpmode(self, task_callback=None):
        """Submits the SetStandbyFPMode command for execution.

        :rtype: tuple
        """
        setstandbyfpmode_command = SetStandbyFPMode(
            self, self.op_state_model, logger=self.logger
        )
        task_status, response = self.submit_task(
            setstandbyfpmode_command.set_standby_fp_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        return task_status, response

    def setstandbylpmode(
        self, setstandbylpmode_command: SetStandbyLPMode, task_callback=None
    ):
        """Submits the SetStandbyLPMode command for execution.

        :rtype: tuple
        """
        task_status, response = self.submit_task(
            setstandbylpmode_command.set_standby_lp_mode,
            args=[self.logger],
            task_callback=task_callback,
        )
        return task_status, response

    def is_command_allowed(self, command_name=None):
        """Checks if the given command is allowed in current operational
        state."""

        if command_name in ["SetStandbyFPMode"]:
            if self.op_state_model.op_state in [
                DevState.FAULT,
                DevState.UNKNOWN,
                DevState.DISABLE,
            ]:
                raise CommandNotAllowed(
                    f"""The invocation of the {command_name} command on this
                    device is not allowed.
                    Reason: The current operational state is
                    {self.op_state_model.op_state}.
                    The command has NOT been executed.
                    This device will continue with normal operation."""
                )
        return True
