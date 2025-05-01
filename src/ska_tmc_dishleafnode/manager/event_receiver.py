"""
Event Receiver for Dish Leaf Node
"""
from __future__ import annotations

import json
from datetime import datetime
from logging import Logger
from time import sleep
from typing import Any, Callable, List

import tango
from ska_tmc_common import (
    DishDeviceInfo,
    DishMode,
    PointingState,
    SdpQueueConnectorDeviceInfo,
)
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
                for attr_name in pointing_model_params_attrs:
                    dish_dev_proxy.subscribe_event(
                        attr_name,
                        tango.EventType.CHANGE_EVENT,
                        self.handle_pointing_model_params,
                        stateless=True,
                    )

            except Exception as exception:
                log_msg = (
                    "Event not working for "
                    f"device {dev_info.dev_name}/{exception}"
                )
                self._logger.exception(log_msg)
            else:
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
                self._logger.exception(log_msg)
            else:
                self.dislnpd_subscribed = True

    # pylint: enable=unused-argument
    def handle_pointing_model_params(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ):
        """Method to handle and update the latest value of dish_pointing_model
        params.

        :parameter event_flag: To flag the change in event for Dishglobalpoing
            params.
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
        self._component_manager.update_dish_pointing_model_param(
            json.dumps(new_value.tolist()), event_flag.attr_value.name
        )
        self.log_event_exit("handle_dish_mode_event")

    def handle_dish_mode_event(
        self: DishLNEventReceiver, event_flag: tango.EventData
    ) -> None:
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
        self.log_event_exit("handle_dish_mode_event")
        self._logger.info(
            "DishMode value updated to %s", DishMode(new_value).name
        )

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
        self.log_event_exit("handle_pointing_state_event")
        self._logger.info(
            "PointingState value updated to %s", PointingState(new_value).name
        )

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
        self._logger.info("ConfiguredBand value updated to %s", new_value)

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
        self.log_event_exit("handle_achieved_pointing_event")

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
                    "Unsubscribed %s Sdp queue connector attribute event.",
                    dev_info.dev_name,
                )
        except Exception as exception:
            log_msg = (
                f"Unable to unsubscribe {dev_info.attribute_name} "
                f"device {dev_info.dev_name}/{exception}"
            )
            self._logger.exception(log_msg)

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
        self.log_event_data(
            event_flag, "handle_pointing_program_track_table_event"
        )
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_flag.device.dev_name()
            )
            return
        new_value = event_flag.attr_value.value
        self._component_manager.update_program_track_table(
            json.loads(new_value)
        )
        self.log_event_exit("handle_pointing_program_track_table_event")

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
        self.log_event_data(
            event_flag, "handle_pointing_program_track_table_event"
        )
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_flag.device.dev_name()
            )
            return
        new_value = event_flag.attr_value.value
        self._logger.debug("New value is %s", new_value)
        if new_value:
            self._logger.debug("Updating track table error value")
            self._component_manager.current_track_table_error = new_value
        self.log_event_exit("handle_pointing_program_track_table_event")
        self._logger.debug(
            "pointingProgramTrackTable error updated to %s", new_value
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
        self.log_event_data(
            event_flag, "handle_pointing_program_track_table_event"
        )
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_flag.device.dev_name()
            )
            return
        new_value = event_flag.attr_value.value
        self._component_manager._update_health_state_callback(new_value)
        self.log_event_exit("handle_pointing_device_healthState_event")
        self._logger.debug(
            "DishLeaf Node pointing device healthState updated to %s",
            new_value,
        )
