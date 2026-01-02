"""
Event Receiver for Dish Leaf Node
"""
from __future__ import annotations

from datetime import datetime
from logging import Logger
from time import sleep
from typing import Any, Callable, List

import tango
from ska_tmc_common import DishDeviceInfo, SdpQueueConnectorDeviceInfo
from ska_tmc_common.log_manager import LogManager
from ska_tmc_common.v1.event_receiver import EventReceiver


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
        attribute_list: dict[str, Callable[..., Any]] | None = None,
        proxy_timeout: int = 500,
        event_subscription_check_period: int = 1,
    ):
        super().__init__(
            component_manager=component_manager,
            logger=logger,
            attribute_list=attribute_list,
            proxy_timeout=proxy_timeout,
            event_subscription_check_period=event_subscription_check_period,
        )
        self.dish_master_subscribed: bool = False
        self.dislnpd_subscribed: bool = False
        self._event_enter_exit_time: List[datetime] = []
        self.log_manager = LogManager()

    def run(self: DishLNEventReceiver) -> None:
        while not self.dish_master_subscribed:
            dishDevInfo = self._component_manager.get_device()
            if dishDevInfo.dev_name:
                self.subscribe_dish_master_events(dishDevInfo)
            sleep(self._event_subscription_check_period)
        while not self.dislnpd_subscribed:
            if self._component_manager.dishln_pointing_dev_name:
                self.subscribe_dishlnpd_events(
                    self._component_manager.dishln_pointing_dev_name
                )
            sleep(self._event_subscription_check_period)

    # pylint: disable=unused-argument
    def subscribe_dish_master_events(
        self: DishLNEventReceiver,
        dev_info: DishDeviceInfo,
        attribute_dictionary=None,
    ) -> None:
        """Subscribe to Dish Master"""
        pointing_model_params_attrs = [
            "band1PointingModelParams",
            "band2PointingModelParams",
            "band3PointingModelParams",
            "band4PointingModelParams",
            "band5APointingModelParams",
            "band5BPointingModelParams",
        ]
        band_capability_attrs = [
            "b1CapabilityState",
            "b2CapabilityState",
            "b3CapabilityState",
            "b4CapabilityState",
            "b5aCapabilityState",
            "b5bCapabilityState",
        ]

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
                    self.handle_command_result_event,
                    stateless=True,
                )
                dish_dev_proxy.subscribe_event(
                    "kValue",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_kvalue_event,
                    stateless=True,
                )
                for attr_name in pointing_model_params_attrs:
                    queue_key = attr_name.lower()
                    # Generate the specific handler method for this attribute
                    handler = self._create_pointing_model_handler(queue_key)
                    dish_dev_proxy.subscribe_event(
                        attr_name,
                        tango.EventType.CHANGE_EVENT,
                        handler,
                        stateless=True,
                    )

                for attr_name in band_capability_attrs:
                    # Generate the specific handler method for this attribute
                    handler = self._create_band_capability_handler(attr_name)
                    dish_dev_proxy.subscribe_event(
                        attr_name,
                        tango.EventType.CHANGE_EVENT,
                        handler,
                        stateless=True,
                    )
                    self._logger.debug(
                        "Subscribed to Dish Master event for"
                        " attribute %s successfully %s",
                        attr_name,
                        dev_info.dev_name,
                    )

            except Exception as exception:
                log_msg = (
                    "Event not working for "
                    f"device {dev_info.dev_name}/{exception}"
                )
                if self.log_manager.is_logging_allowed(
                    "event_receiver_exception"
                ):
                    self._logger.exception(log_msg)
            else:
                self._logger.debug(
                    "Subscribed to Dish Master events for device successful"
                    " %s",
                    dev_info.dev_name,
                )
                self.dish_master_subscribed = True

    def subscribe_dishlnpd_events(
        self: DishLNEventReceiver,
        dlnPointingDev_name: str,
        attribute_dictionary=None,
    ) -> None:
        """
        Subscribe to DishLeaf Node Pointing Device events.

        Parameters
        ----------
        self : DishLNEventReceiver
            The DishLNEventReceiver instance.
        dlnPointingDev_name : str
            The name of the DishLeaf Node Pointing Device to
            subscribe to.
        attribute_dictionary : Optional[dict]
            Dictionary containing attribute configurations for the
            subscription.
            Defaults to None.

        Returns
        -------
        None

        Notes
        -----
        This method establishes event subscriptions for a
        DishLeaf Node Pointing Device using the provided
        device name and optional attribute configurations.
        """
        with tango.EnsureOmniThread():
            try:
                dishln_pointing_dev_proxy = self._dev_factory.get_device(
                    dlnPointingDev_name
                )
                dishln_pointing_dev_proxy.subscribe_event(
                    "pointingProgramTrackTable",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_pointing_program_track_table_event,
                    stateless=True,
                )
                dishln_pointing_dev_proxy.subscribe_event(
                    "programTrackTableError",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_program_track_table_error_event,
                    stateless=True,
                )
                dishln_pointing_dev_proxy.subscribe_event(
                    "healthState",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_dishlnpd_healthState_event,
                    stateless=True,
                )
            except Exception as exception:
                log_msg = (
                    "Event not working for "
                    f"device {dlnPointingDev_name}/{exception}"
                )
                if self.log_manager.is_logging_allowed(
                    "event_receiver_exception"
                ):
                    self._logger.exception(log_msg)
            else:
                self.dislnpd_subscribed = True

    def _create_pointing_model_handler(self, queue_key: str) -> Callable:
        """
        A function that generates a specific handler function for a
        given queue key(attribute name).
        """

        def generic_handler(event_flag: tango.EventData):
            """
            Generic handler method for updating pointing model parameters
            using the single optimized manager method.

            Updates the band* pointing model parameters event in the respective
            queue.
            * :-> 1, 2, 3, 4, 5a, 5b.
            Args:
                queue_key (str): The dictionary key for the specific event
                queue (e.g., "band1pointingmodelparams").
                event (tango.EventData): It is the Tango Event Data object
                    which contains the event data.
            """

            self._component_manager.event_queues[queue_key].put(event_flag)

        return generic_handler

    def _create_band_capability_handler(self, queue_key: str) -> Callable:
        """
        A function that generates a specific handler function for a
        given band capability queue key(attribute name).
        """

        def generic_handler(event_flag: tango.EventData):
            """
            Generic handler method for updating band capability state
            using the single optimized manager method.

            Updates the band* capability state event in the respective
            queue.
            * :-> 1, 2, 3, 4, 5a, 5b.
            Args:
                queue_key (str): The dictionary key for the specific event
                queue (e.g., "b1aCapabilityState").
                event (tango.EventData): It is the Tango Event Data object
                    which contains the event data.
            """

            self._component_manager.event_queues[queue_key].put(event_flag)

        return generic_handler

    def handle_dish_mode_event(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of dishMode attribute.

        :parameter event_flag: To flag the change in event for dishMode.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self._component_manager.update_dish_mode_event(event_flag)

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

        self._component_manager.update_pointing_state_event(event_flag)

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

        self._component_manager.update_configured_band_event(event_flag)

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

        # self._component_manager.update_achieved_pointing_event(event_flag)

        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure()
            return
        new_value = event_flag.attr_value.value
        self._component_manager.achieved_pointing_data.put(new_value)

    def handle_kvalue_event(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ) -> None:
        """
        Handle kValue change event received from the Dish Master.

        Args:
            event_flag (tango.EventData): Tango event data containing
            the updated kValue or error information.

        Returns:
            None
        """
        self._component_manager.update_kvalue_event(event_flag)

    def subscribe_sdpqc_attribute(
        self: DishLNEventReceiver,
        dev_info: SdpQueueConnectorDeviceInfo,
        attribute_name: str,
    ) -> None:
        """Subscribe to the given SDP queue connector attribute

        Args:
            dev_info (SdpQueueConnectorDeviceInfo): device info.
            attribute_name (str): Attribute name to be subscribed.

        """
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
        """UnSubscribe to the given SDP queue connector attribute

        Args:
            dev_info (SdpQueueConnectorDeviceInfo): device info.
        """
        try:
            if dev_info.event_id:
                sdp_queue_connector_proxy = self._dev_factory.get_device(
                    dev_info.dev_name
                )
                sdp_queue_connector_proxy.unsubscribe_event(dev_info.event_id)
                dev_info.event_id = 0
                dev_info.subscribed_to_attribute = False
                self._logger.info(
                    "Unsubscribed %s Sdp queue connector attribute event.",
                    dev_info.dev_name,
                )
        except Exception as exception:
            log_msg = (
                f"Unable to unsubscribe {dev_info.attribute_name} "
                f"device {dev_info.dev_name}/{exception}"
            )
            self._logger.exception(log_msg)

    def handle_pointing_program_track_table_event(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        pointingProgramTrackTable attribute.

        :parameter event_flag: To flag the change in event
            for programTrackTable.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self._component_manager.update_pointing_program_track_table_event(
            event_flag
        )

    def handle_program_track_table_error_event(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        program track table error attribute.

        :parameter event_flag: To flag the change in event
            for programTrackTableError.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self._component_manager.update_program_track_table_error_event(
            event_flag
        )

    def handle_dishlnpd_healthState_event(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of
        pointing device healthState. If this value/event is
        unavailable, DishLeaf node healthState is shown as
        DEGRADED.

        :parameter event_flag: To flag the change in event
            for programTrackTable.
        :type event_flag: tango.EventType.CHANGE_EVENT
        :return: None
        :rtype: NoneType
        """

        self._component_manager.update_health_state_event(event_flag)
