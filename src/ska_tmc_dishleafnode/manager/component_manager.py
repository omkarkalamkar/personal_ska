"""
This module provided a reference implementation of a BaseComponentManager.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import time

from ska_tmc_common.command_executor import CommandExecutor
from ska_tmc_common.device_info import DeviceInfo
from ska_tmc_common.tmc_component_manager import TmcLeafNodeComponentManager

from ska_tmc_dishleafnode.manager.event_receiver import DishLNEventReceiver


class DishLNComponentManager(TmcLeafNodeComponentManager):
    """
    A component manager for The Dish Leaf Node component.

    It supports:

    * Monitoring its component, e.g. detect that it has been turned off
      or on
    """

    def __init__(
        self,
        dish_dev_name,
        op_state_model,
        logger=None,
        _update_device_callback=None,
        _update_command_in_progress_callback=None,
        _monitoring_loop=False,
        _event_receiver=True,
        max_workers=5,
        proxy_timeout=500,
        sleep_time=1,
    ):
        """
        Initialise a new ComponentManager instance.

        :param op_state_model: the op state model used by this component
            manager
        :param logger: a logger for this component manager
        :param _component: allows setting of the component to be
            managed; for testing purposes only
        """
        super().__init__(
            op_state_model,
            logger,
            _monitoring_loop,
            _event_receiver,
            max_workers,
            proxy_timeout,
            sleep_time,
        )

        self.update_device_info(dish_dev_name)
        if _event_receiver:
            self._event_receiver = DishLNEventReceiver(
                self,
                logger,
                proxy_timeout=proxy_timeout,
                sleep_time=sleep_time,
            )
            self._event_receiver.start()

        self.command_executor = CommandExecutor(
            logger,
            _update_command_in_progress_callback=_update_command_in_progress_callback,
        )

    def stop(self):
        self._event_receiver.stop()

    def get_device(self):
        """
        Return the device info our of the monitoring loop with name dev_name

        :param None:
        :return: a device info
        :rtype: DeviceInfo
        """
        return self._device

    def update_device_info(self, dish_dev_name):
        self._dish_dev_name = dish_dev_name
        self._device = DeviceInfo(self._dish_dev_name, False)

    def device_failed(self, exception):
        """
        Return the list of the checked monitored devices

        :return: list of the checked monitored devices
        """
        result = []
        # check below statement
        for dev in self.component.devices:
            if dev.unresponsive:
                result.append(dev)
                continue
            if dev.ping > 0:
                result.append(dev)
                continue
            if dev.last_event_arrived is not None:
                result.append(dev)
                continue
        return result

    def update_event_failure(self):
        with self.lock:
            dev_info = self.get_device()
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)
