"""
Event Receiver for Dish Leaf Node
"""
from __future__ import annotations

from logging import Logger
from time import sleep
from typing import Any, Callable

import tango
from ska_tmc_common import (
    DishDeviceInfo,
    EventReceiver,
    SdpQueueConnectorDeviceInfo,
)


class DishLNEventReceiver(EventReceiver):
    """
    The DishLNEventReceiver class has the responsibility to receive events
    from the dish master managed by the Dish Leaf Node.

    The ComponentManager uses to handle events methods
    for the attribute of interest.
    For each of them a callback is defined.
    """

    def __init__(
        self: DishLNEventReceiver,
        component_manager,
        logger: Logger,
        attribute_dict: dict[str, Callable[..., Any]] | None = None,
        proxy_timeout: int = 500,
        sleep_time: int = 1,
    ):
        super().__init__(
            component_manager=component_manager,
            logger=logger,
            attribute_dict=attribute_dict,
            proxy_timeout=proxy_timeout,
            sleep_time=sleep_time,
        )
        self.subscribed: bool = False

    def run(self: DishLNEventReceiver) -> None:
        while not self.subscribed:
            dishDevInfo = self._component_manager.get_device()
            if dishDevInfo.dev_name:
                self.subscribe_events(dishDevInfo)
            sleep(self._sleep_time)

    def subscribe_events(
        self: DishLNEventReceiver,
        dev_info: DishDeviceInfo,
        attribute_dictionary=None,
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

    def handle_dish_mode_event(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of dishMode attribute.

        :parameter event_flag: To flag the change in event for dishMode.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
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

    def handle_pointing_state_event(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        pointingState attribute.

        :parameter event_flag: To flag the change in event for pointingState.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
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

    def handle_configured_band_event(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        configuredBand attribute.

        :parameter event_flag: To flag the change in event for configuredBand.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
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

    def handle_achieved_pointing_event(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        achievedPointing attribute.

        :parameter event_flag: To flag the change in event for
            achievedPointing.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
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

    def handle_long_running_command_result(
        self: DishLNEventReceiver, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        longRunningCommandResult attribute.

        :parameter event_flag: To flag the change in event.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
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
            new_value
        )
        self._logger.info(f"long running command value updated to {new_value}")

    def subscribe_sdpqc_attribute(
        self: DishLNEventReceiver,
        dev_info: SdpQueueConnectorDeviceInfo,
        attribute_name: str,
    ) -> None:
        """Subscribe to the given SDP queue connector attribute"""
        # Initialized to avoid linting issue.
        TIMEOUT = 120
        elapsed_time = 0
        while not dev_info.subscribed_to_attribute and elapsed_time < TIMEOUT:
            try:
                sdp_queue_connector = self._dev_factory.get_device(
                    dev_info.dev_name
                )
                if sdp_queue_connector.ping() > 0:
                    dev_info.event_id = sdp_queue_connector.subscribe_event(
                        attribute_name,
                        tango.EventType.CHANGE_EVENT,
                        self._component_manager.process_pointing_calibration,
                        stateless=True,
                    )
                    dev_info.subscribed_to_attribute = True
            except Exception as exception:
                log_msg = (
                    f"Unable to subscribe {attribute_name} "
                    f"device {dev_info.dev_name}/{exception}"
                )
                self._logger.exception(log_msg)
                elapsed_time = elapsed_time + 1
                sleep(1)

    def unsubscribe_sdpqc_attribute(
        self: DishLNEventReceiver, dev_info: SdpQueueConnectorDeviceInfo
    ) -> None:
        """Subscribe to the given SDP queue connector attribute"""
        try:
            if dev_info.event_id:
                sdp_queue_connector_proxy = self._dev_factory.get_device(
                    dev_info.dev_name
                )
                sdp_queue_connector_proxy.unsubscribe_event(dev_info.event_id)
                dev_info.event_id = 0
                dev_info.subscribed_to_attribute = False
                self._logger.info(
                    "Unsubscribed %s Sdp queuue connector attribute event.",
                    dev_info.dev_name,
                )
        except Exception as exception:
            log_msg = (
                f"Unable to unsubscribe {dev_info.attribute_name} "
                f"device {dev_info.dev_name}/{exception}"
            )
            self._logger.exception(log_msg)
