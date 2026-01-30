"""
Event Manager for Dish Leaf Node
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import tango
from ska_ser_logging import configure_logging
from ska_tmc_common.v2.event_manager import EventManager

configure_logging("DEBUG")

LOGGER = logging.getLogger(__name__)


class DishLNEventManager(EventManager):
    """
    DishLNEventManager class inherits from EventManager and
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
        self.pointing_model_params_attrs = [
            "band1PointingModelParams",
            "band2PointingModelParams",
            "band3PointingModelParams",
            "band4PointingModelParams",
            "band5APointingModelParams",
            "band5BPointingModelParams",
        ]
        self.band_capability_attrs = [
            "b1CapabilityState",
            "b2CapabilityState",
            "b3CapabilityState",
            "b4CapabilityState",
            "b5aCapabilityState",
            "b5bCapabilityState",
        ]
        self.logger = logger
        for model_params in self.pointing_model_params_attrs:
            method_name = f"{model_params.lower()}_event_callback"
            setattr(self, method_name, self.handle_pointing_model_params)

        for model_params in self.band_capability_attrs:
            method_name = f"{model_params.lower()}_event_callback"
            setattr(self, method_name, self.handle_band_capabilities)

    def unsubscribe_events(self, device_name, attribute_names=None):
        with tango.EnsureOmniThread():
            super().unsubscribe_events(device_name, attribute_names)

    # pylint: enable=unused-argument
    def handle_pointing_model_params(
        self: DishLNEventManager, event_data: tango.EventData
    ):
        """Method to handle and update the latest value of dish_pointing_model
        params.

        :parameter event_data: The change event data for Dish
          global pointing model params.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        if event_data.attr_value:
            band_param = event_data.attr_value.name.lower()
            self._component_manager.event_queues[band_param].put(event_data)

    # pylint: enable=unused-argument
    def handle_band_capabilities(
        self: DishLNEventManager, event_data: tango.EventData
    ):
        """Method to handle and update the latest value of Band capabilities
        params.

        :parameter event_data: The change event data for Dish
          global pointing model params.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        if event_data.attr_value:
            band_capability = event_data.attr_value.name.lower()
            self._component_manager.event_queues[band_capability].put(
                event_data
            )

    def dishmode_event_callback(
        self: DishLNEventManager, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of dishMode attribute.

        :parameter event_data: The change event data for dishMode.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self._component_manager.event_queues["dishMode"].put(event_data)

    def pointingstate_event_callback(
        self: DishLNEventManager, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        pointingState attribute.

        :parameter event_data: The change event data for pointingState.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self._component_manager.event_queues["pointingState"].put(event_data)

    def configuredband_event_callback(
        self: DishLNEventManager, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        configuredBand attribute.

        :parameter event_data: The change event data for configuredBand.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self._component_manager.event_queues["configuredBand"].put(event_data)

    def achievedpointing_event_callback(
        self: DishLNEventManager, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        achievedPointing attribute.

        :parameter event_data: The change event data for
            achievedPointing.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        if event_data.attr_value:
            new_value = event_data.attr_value.value
            self._component_manager.achieved_pointing_data.put(new_value)

    def pointingprogramtracktable_event_callback(
        self: DishLNEventManager, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        pointingProgramTrackTable attribute.

        :parameter event_data: The change event data
            for programTrackTable.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self._component_manager.event_queues["pointingProgramTrackTable"].put(
            event_data
        )

    def programtracktableerror_event_callback(
        self: DishLNEventManager, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        program track table error attribute.

        :parameter event_data: The change event data
            for programTrackTableError.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self._component_manager.event_queues["programTrackTableError"].put(
            event_data
        )

    def healthstate_event_callback(
        self: DishLNEventManager, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        pointing device healthState. If this value/event is
        unavailable, DishLeaf node healthState is shown as
        DEGRADED.

        :parameter event_data: The change event data
            for programTrackTable.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self._component_manager.event_queues["healthState"].put(event_data)

    def longrunningcommandresult_event_callback(
        self, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        longRunningCommandResult attribute.

        :parameter event_data: The change event data
            for longRunningCommandResult.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        self._component_manager.event_queues["longRunningCommandResult"].put(
            event_data
        )

    def humidity_event_callback(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of
        humidity attribute.

        :parameter event_data: The change event data
            for humidity.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        attr_name = "humidity" + event_data.device.dev_name()
        self._component_manager.event_queues[attr_name].put(event_data)

    def pressure_event_callback(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of
        pressure attribute.

        :parameter event_data: The change event data
            for pressure.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        attr_name = "pressure" + event_data.device.dev_name()
        self._component_manager.event_queues[attr_name].put(event_data)

    def temperature_event_callback(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of
        temperature attribute.

        :parameter event_data: The change event data
            for temperature.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        attr_name = "temperature" + event_data.device.dev_name()
        self._component_manager.event_queues[attr_name].put(event_data)

    def windspeed_event_callback(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of
        windspeed attribute.

        :parameter event_data: The change event data
            for windspeed.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        attr_name = "windSpeed" + event_data.device.dev_name()
        self._component_manager.event_queues[attr_name].put(event_data)

    def kvalue_event_callback(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of
        kvalue attribute.

        :parameter event_data: The change event data
            for kvalue.
        :type event_data: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """
        self._component_manager.event_queues["kValue"].put(event_data)
