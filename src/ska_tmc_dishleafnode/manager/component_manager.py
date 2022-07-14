"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
# pylint: disable=abstract-method
from ska_tmc_common.command_executor import CommandExecutor
from ska_tmc_common.device_info import DishDeviceInfo
from ska_tmc_common.event_receiver import EventReceiver
from ska_tmc_common.liveliness_probe import SingleDeviceLivelinessProbe
from ska_tmc_common.tmc_component_manager import TmcLeafNodeComponentManager

from ska_tmc_dishleafnode.commands.setstandbyfpmode_command import (
    SetStandbyFPMode,
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

        self._event_receiver = None
        # As of now EventReciever is not being used.
        if event_receiver:
            self._event_receiver = EventReceiver(
                self, logger, max_workers, proxy_timeout, sleep_time
            )
            self._event_receiver.start()
        else:
            logger.warning("Event reciever is not running")

        # It will be removed
        self.command_executor = CommandExecutor(
            logger,
            _update_command_in_progress_callback=update_command_in_progress_callback,  # noqa: E501
        )

        self.timeout = timeout
        self.dish_dev_name = dish_dev_name

    def setstandbyfpmode(self, task_callback=None):
        """Submits the SetStandbyFPMode command for execution.

        :rtype: tuple
        """
        setstandbyfpmode_command = SetStandbyFPMode
        task_status, response = self.submit_task(
            setstandbyfpmode_command.set_standby_fp_mode,
            self.logger,
            task_callback=task_callback,
        )
        return task_status, response
