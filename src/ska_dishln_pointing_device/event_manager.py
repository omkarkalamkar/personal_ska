"""
Event Manager for Dish Leaf Node ponting device.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import tango
from ska_ser_logging import configure_logging
from ska_tmc_common.v2.event_manager import EventManager

configure_logging("DEBUG")

LOGGER = logging.getLogger(__name__)


class DishLNPDEventManager(EventManager):
    """
    DishLNPDEventManager class inherits from EventManager and
    adds event callbacks.
    """

    def __init__(
        self,
        component_manager,
        subscription_configuration: Optional[dict[str, list]] = None,
        logger: logging.Logger = LOGGER,
        stateless: bool = True,
        event_subscription_check_period: int = 1,
        event_error_max_count: int = 10,
        status_update_callback: Optional[Callable] = None,
        maximum_status_queue_size: int = 50,
    ) -> None:
        super().__init__(
            component_manager,
            subscription_configuration,
            logger,
            stateless,
            event_subscription_check_period,
            event_error_max_count,
            status_update_callback,
            maximum_status_queue_size,
        )

        self._component_manager = component_manager

    def humidity_event_callback(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of
        humidity attribute.

        :parameter event_data: The change event data
            for humidity.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        self._component_manager.event_queues["humidity"].put(event_data)

    def pressure_event_callback(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of
        pressure attribute.

        :parameter event_data: The change event data
            for pressure.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        self._component_manager.event_queues["pressure"].put(event_data)

    def temperature_event_callback(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of
        temperature attribute.

        :parameter event_data: The change event data
            for temperature.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        self._component_manager.event_queues["temperature"].put(event_data)

    def windspeed_event_callback(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of
        windspeed attribute.

        :parameter event_data: The change event data
            for windspeed.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        self._component_manager.event_queues["windSpeed"].put(event_data)
