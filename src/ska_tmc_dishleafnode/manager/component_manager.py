"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
import time

from ska_tmc_common.command_executor import CommandExecutor

# from ska_tmc_common.device_info import DeviceInfo
from ska_tmc_common.tmc_component_manager import TmcLeafNodeComponentManager

from ska_tmc_dishleafnode.device_info import DishDeviceInfo
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
        :param _monitoring_loop: allows eanabling/disabling the monitoring loop; For DishLN
        monitoring loop is not required. Therefore this parameter will always be False.
        :param _event_receiver: allows eanabling/disabling the event subscriber;
        :param max_workers: allows to specify number of threads to be used by the monitoring loop;
        This parameter is not used for DishLN.
        :param proxy_timeout: allows to specify a client side timeout for sub-devices in milliseconds
        used by the monitoring loop; This parameter is not used for DishLN.
        :param sleep_time: allows to specify the wait between each iteration of the monitoring loop
        and EventSubscriber;
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
        Return the device info for the specified Dish device.

        :param dish_dev_name: Name of Dish device.
        :return: Dish device info
        :rtype: DishDeviceInfo
        """
        return self._device

    def update_device_info(self, dish_dev_name):
        self._dish_dev_name = dish_dev_name
        self._device = DishDeviceInfo(self._dish_dev_name, False)

    @property
    def checked_device(self):
        """
        Return the checked dish device

        :return: the checked dish device
        """
        if (self._device.unresponsive) or (
            self._device.last_event_arrived is not None
        ):
            return self._device
        return None

    def update_event_failure(self):
        with self.lock:
            dev_info = self.get_device()
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)

    def update_device_dish_mode(self, dish_mode):
        """
        Update a monitored device dish Mode,
        and call the relative callbacks if available

        :param dish_mode: Dish Mode of the Dish device
        :type dish_mode: DishMode
        """
        with self.lock:
            dev_info = self.get_device()
            dev_info.dishMode = dish_mode
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)

    def update_device_pointing_state(self, pointing_state):
        """
        Update a monitored device pointing State,
        and call the relative callbacks if available

        :param pointing State: pointing State of the device
        :type pointing State: pointingState
        """
        with self.lock:
            dev_info = self.get_device()
            dev_info.pointingState = pointing_state
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)

    def update_device_rxcapturing_data(self, capturing_data):
        """
        Update a monitored device data capturing,
        and call the relative callbacks if available

        :param capturing_data: capturing data of the device
        :type rxcapturing Data: Boolean
        """
        with self.lock:
            dev_info = self.get_device()
            dev_info.rxCapturingData = capturing_data
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)

    def update_device_achieved_pointing(self, achieved_pointing):
        """
        Update a monitored device achieved Pointing,
        and call the relative callbacks if available

        :param achieved Pointing: achieved pointing of the device
        :type achieved Pointing Data: DevDouble array
        """
        with self.lock:
            dev_info = self.get_device()
            dev_info.achievedpointing = achieved_pointing
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)

    def update_device_desired_pointing(self, desired_pointing):
        """
        Update a monitored device desired Pointing,
        and call the relative callbacks if available

        :param desiredPointing: desiredPointing of the device
        :type desired Pointing : DevDouble array
        """
        with self.lock:
            dev_info = self.get_device()
            dev_info.desiredPointing = desired_pointing
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)
