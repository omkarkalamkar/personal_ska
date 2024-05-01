"""
Event Receiver for Dish Leaf Node
"""
from datetime import datetime
from logging import Logger
from time import sleep
from typing import Any, Callable, List

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

    def __init__(
        self,
        component_manager,
        logger: Logger,
        attribute_dict: dict[str, Callable[..., Any]] | None = None,
        max_workers: int = 1,
        proxy_timeout: int = 500,
        sleep_time: int = 1,
    ):
        super().__init__(
            component_manager=component_manager,
            logger=logger,
            attribute_dict=attribute_dict,
            max_workers=max_workers,
            proxy_timeout=proxy_timeout,
            sleep_time=sleep_time,
        )
        self.subscribed: bool = False
        self._event_enter_exit_time: List[datetime] = []

    def run(self) -> None:
        while not self.subscribed:
            dishDevInfo = self._component_manager.get_device()
            if dishDevInfo.dev_name:
                self.subscribe_events(dishDevInfo)
            sleep(self._sleep_time)

    def subscribe_events(
        self, dev_info: DishDeviceInfo, attribute_dictionary=None
    ) -> None:
        with tango.EnsureOmniThread():
            try:
                dish_dev_proxy = self._dev_factory.get_device(
                    dev_info.dev_name
                )
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

                dish_dev_proxy.subscribe_event(
                    "configuredBand",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_configured_band_event,
                    stateless=True,
                )
                dish_dev_proxy.subscribe_event(
                    "longRunningCommandStatus",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_long_running_command_status,
                    stateless=True,
                )
                dish_dev_proxy.subscribe_event(
                    "longRunningCommandResult",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_long_running_command_result,
                    stateless=True,
                )
            except Exception as exception:
                log_msg = (
                    "Event not working for "
                    f"device {dev_info.dev_name}/{exception}"
                )
                self._logger.exception(log_msg)
            else:
                self.subscribed = True

    def handle_dish_mode_event(self, event_flag: tango.EventData) -> None:
        """Method to handle and update the latest value of dishMode attribute.

        :parameter event_flag: To flag the change in event for dishMode.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        self.log_event_data(event_flag, "handle_dish_mode_event")
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_flag.device.dev_name()
            )
            return
        new_value = event_flag.attr_value.value
        self._component_manager.update_device_dish_mode(new_value)
        self._logger.info(f"DishMode value updated to {new_value}")
        self.log_event_exit("handle_dish_mode_event")

    def handle_pointing_state_event(self, event_flag: tango.EventData) -> None:
        """Method to handle and update the latest value of
        pointingState attribute.

        :parameter event_flag: To flag the change in event for pointingState.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self.log_event_data(event_flag, "handle_pointing_state_event")
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_flag.device.dev_name()
            )
            return
        new_value = event_flag.attr_value.value
        self._component_manager.update_device_pointing_state(new_value)
        self._logger.info(f"PointingState value updated to {new_value}")
        self.log_event_exit("handle_pointing_state_event")

    def handle_configured_band_event(
        self, event_flag: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        configuredBand attribute.

        :parameter event_flag: To flag the change in event for configuredBand.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        self.log_event_data(event_flag, "handle_configured_band_event")
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_flag.device.dev_name()
            )
            return
        new_value = event_flag.attr_value.value
        self._component_manager.update_device_configured_band(new_value)
        self._logger.info(f"ConfiguredBand value updated to {new_value}")
        self.log_event_exit("handle_configured_band_event")

    def handle_achieved_pointing_event(
        self, event_flag: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        achievedPointing attribute.

        :parameter event_flag: To flag the change in event for
            achievedPointing.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self.log_event_data(event_flag, "handle_achieved_pointing_event")
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_flag.device.dev_name()
            )
            return
        new_value = event_flag.attr_value.value
        self._component_manager.achieved_pointing_data.put(new_value)
        self._logger.debug(f"achievedPointing value is updated to {new_value}")
        self.log_event_exit("handle_achieved_pointing_event")

    def handle_long_running_command_status(
        self, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        longRunningCommandStatus attribute.

        :parameter event_flag: To flag the change in event.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self.log_event_data(event_data, "handle_long_running_command_status")
        if event_data.err:
            error = event_data.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_data.device.dev_name()
            )
            return
        new_value = event_data.attr_value.value

        self._component_manager.update_device_long_running_command_status(
            new_value
        )
        self._logger.info(f"long running command value updated to {new_value}")
        self.log_event_exit("handle_long_running_command_status")

    def handle_long_running_command_result(
        self, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        longRunningCommandResult attribute.

        :parameter event_flag: To flag the change in event.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self.log_event_data(event_data, "handle_long_running_command_result")
        if event_data.err:
            error = event_data.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_data.device.dev_name()
            )
            return
        new_value = event_data.attr_value.value
        self._component_manager.update_device_long_running_command_result(
            event_data.device.dev_name(), new_value
        )
        self._logger.info(
            f"longRunningCommandResult value updated to {new_value}"
        )
        self.log_event_exit("handle_long_running_command_result")

    def log_event_data(
        self, event_data: tango.EventData, callback_name: str
    ) -> None:
        """Log the event data for later use."""
        if event_data.attr_value:
            attribute_name = event_data.attr_value.name
            attribute_value = event_data.attr_value.value
            reception_time: datetime = event_data.attr_value.time.todatetime()
            current_time = datetime.utcnow()
            self._event_enter_exit_time.append(current_time)
            current_time = current_time.strftime("%d/%m/%Y %H:%M:%S:%f")
            self._logger.info(
                "Enter time for the callback: %s is %s. Event data is - "
                + "Attribute: %s, Value: %s, Reception time: %s",
                callback_name,
                current_time,
                attribute_name,
                attribute_value,
                reception_time.strftime("%d/%m/%Y %H:%M:%S:%f"),
            )

    def log_event_exit(self, callback_name: str) -> None:
        """Log the time of exiting the event."""
        self._event_enter_exit_time.append(datetime.utcnow())
        if len(self._event_enter_exit_time) == 2:
            time_diff = (
                self._event_enter_exit_time[1] - self._event_enter_exit_time[0]
            ).total_seconds()
        else:
            time_diff = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S:%f")
        self._event_enter_exit_time.clear()
        self._logger.info(
            "Exit time for the callback: %s is %s",
            callback_name,
            time_diff,
        )
