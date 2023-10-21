"""Event Receiver for Dish Leaf Node"""
from concurrent import futures
from time import sleep

import tango
from ska_tmc_common import DishDeviceInfo, EventReceiver


class DishLNEventReceiver(EventReceiver):
    """
    The DishLNEventReceiver class has the responsibility to receive events
    from the dish master managed by the Dish Leaf Node.

    The ComponentManager uses to handle events methods
    for the attribute of interest.
    For each of them a callback is defined.
    """

    def run(self) -> None:
        while not self._stop:
            with futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                dishDevInfo = self._component_manager.get_device()
                if dishDevInfo.last_event_arrived is None:
                    executor.submit(self.subscribe_events, dishDevInfo)
            sleep(self._sleep_time)

    def subscribe_events(self, dev_info: DishDeviceInfo, attribute_dictionary=None) -> None:
        super().subscribe_events(dev_info, self.attribute_dictionary)
        try:
            dish_dev_proxy = self._dev_factory.get_device(dev_info.dev_name)
            dish_dev_proxy.subscribe_event(
                "dishMode",
                tango.EventType.CHANGE_EVENT,
                self.handle_dish_mode_event,
                stateless=True,
            )

            dish_dev_proxy.subscribe_event(
                "pointingState",
                tango.EventType.CHANGE_EVENT,
                self.handle_pointing_state_event,
                stateless=True,
            )

            dish_dev_proxy.subscribe_event(
                "achievedPointing",
                tango.EventType.CHANGE_EVENT,
                self.handle_achieved_pointing_event,
                stateless=True,
            )

        except Exception as e:
            log_msg = f"Event not working for device {dish_dev_proxy.dev_name}/{e}"
            self._logger.exception(log_msg)

    def handle_dish_mode_event(self, event_flag: tango.EventData) -> None:
        """Method to handle and update the latest value of dishMode
        attribute.

        Args:
            event_flag (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure()
            return
        new_value = event_flag.attr_value.value
        self._component_manager.update_device_dish_mode(new_value)
        self._logger.info(f"DishMode value updated to {new_value}")

    def handle_pointing_state_event(self, event_flag: tango.EventData) -> None:
        """Method to handle and update the latest value of
        pointingState attribute.

        Args:
            event_flag (tango.EventData): to flag the
            change in event.
        """
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure()
            return
        new_value = event_flag.attr_value.value
        self._component_manager.update_device_pointing_state(new_value)
        self._logger.info(f"PointingState value updated to {new_value}")

    def handle_achieved_pointing_event(self, event_flag: tango.EventData) -> None:
        """Method to handle and update the latest value of
        achievedPointing attribute.

        Args:
            event_flag (tango.EventData): to flag the
            change in event.
        """
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure()
            return
        new_value = event_flag.attr_value.value
        self._component_manager.update_achieved_pointing(new_value)
        self._logger.info(f"achievedPointing value is updated to {new_value}")
