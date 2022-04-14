import threading
from time import sleep

import tango
from ska_tmc_common.event_receiver import EventReceiver


class DishLNEventReceiver(EventReceiver):
    """
    The DishLNEventReceiver class has the responsibility to receive events
    from Dish device.

    The ComponentManager uses the handle events methods
    for the attribute of interest.
    For each of them a callback is defined.

    """

    def __init__(
        self,
        component_manager,
        logger=None,
        max_workers=1,
        proxy_timeout=500,
        sleep_time=1,
    ):
        super().__init__(
            component_manager, logger, max_workers, proxy_timeout, sleep_time
        )
        self._thread = threading.Thread(target=self.subscribe_events)
        self._max_workers = max_workers
        self._sleep_time = sleep_time
        self._stop = False
        self._component_manager = component_manager

    def subscribe_events(self, devInfo):
        while not self._stop:
            dev_info = self._component_manager.get_device()
            if dev_info.last_event_arrived is None:
                try:
                    proxy = self._dev_factory.get_device(devInfo.dev_name)
                    proxy.subscribe_event(
                        "dishMode",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_dish_mode_event,
                        stateless=True,
                    )

                except Exception as e:
                    self._logger.debug(
                        "dishmode not working for device %s/%s",
                        proxy.dev_name,
                        e,
                    )

                try:
                    proxy.subscribe_event(
                        "pointingState",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_pointing_state_event,
                        stateless=True,
                    )
                except Exception as e:
                    self._logger.debug(
                        "pointintState is not working for device %s/%s",
                        proxy.dev_name,
                        e,
                    )

                try:
                    proxy.subscribe_event(
                        "achievedPointing",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_achieved_pointing_event,
                        stateless=True,
                    )
                except Exception as e:
                    self._logger.debug(
                        "achievedpointing not working for device %s/%s",
                        proxy.dev_name,
                        e,
                    )

                try:
                    proxy.subscribe_event(
                        "desiredPointing",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_desired_pointing_event,
                        stateless=True,
                    )
                except Exception as e:
                    self._logger.debug(
                        "desiredPointing not working for device %s/%s",
                        proxy.dev_name,
                        e,
                    )

                try:
                    proxy.subscribe_event(
                        "rxCapturingData",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_rxcapturing_event,
                        stateless=True,
                    )
                except Exception as e:
                    self._logger.debug(
                        "rxCapturingData not working for device %s/%s",
                        proxy.dev_name,
                        e,
                    )
            sleep(self._sleep_time)

    def handle_dish_mode_event(self, evt):
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            self._component_manager.update_event_failure()
            return
        new_value = evt.attr_value.value
        self._component_manager.update_device_dish_mode(new_value)
        self._logger.info("dishMode value is updated")

    def handle_pointing_state_event(self, evt):
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            self._component_manager.update_event_failure()
            return
        new_value = evt.attr_value.value
        self._component_manager.update_device_pointing_State(new_value)
        self._logger.info("pointingState value is updated")

    def handle_achieved_pointing_event(self, evt):
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            self._component_manager.update_event_failure()
            return
        new_value = evt.attr_value.value
        self._component_manager.update_device_achieved_pointing(new_value)
        self._logger.info("achievedPointing value is updated")

    def handle_desired_pointing_event(self, evt):
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            self._component_manager.update_event_failure()
            return
        new_value = evt.attr_value.value
        self._component_manager.update_device_desired_pointing(new_value)
        self._logger.info("desiredPointing value is updated")

    def handle_rxcapturing_event(self, evt):
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            self._component_manager.update_event_failure()
            return
        new_value = evt.attr_value.value
        self._component_manager.update_device_rxcapturing_data(new_value)
        self._logger.info("rxCapturingData value is updated")
