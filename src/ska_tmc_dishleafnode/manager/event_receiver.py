"""Event Receiver for Dish Leaf Node"""
from concurrent import futures
from time import sleep

import tango
from ska_tmc_common.device_info import DeviceInfo
from ska_tmc_common.event_receiver import EventReceiver


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
        logger=None,
        max_workers: int = 1,
        proxy_timeout: int = 500,
        sleep_time: int = 1,
    ):
        super().__init__(
            component_manager, logger, max_workers, proxy_timeout, sleep_time
        )
        self._max_workers = max_workers
        self._sleep_time = sleep_time
        self._stop = False
        self._component_manager = component_manager

    def run(self) -> None:
        while not self._stop:
            with futures.ThreadPoolExecutor(
                max_workers=self._max_workers
            ) as executor:
                devInfo = self._component_manager.get_device()
                if devInfo.last_event_arrived is None:
                    executor.submit(self.subscribe_events, devInfo)
            sleep(self._sleep_time)

    def subscribe_events(self, dev_info: DeviceInfo) -> None:
        try:
            proxy = self._dev_factory.get_device(dev_info.dev_name)
            proxy.subscribe_event(
                "dishMode",
                tango.EventType.CHANGE_EVENT,
                self.handle_dish_mode_event,
                stateless=True,
            )

        except Exception as e:
            log_msg = f"event not working for device {proxy.dev_name}/{e}"
            self._logger.debug(log_msg)

    def handle_dish_mode_event(
        self, evt: tango.EventType.CHANGE_EVENT
    ) -> None:
        if evt.err:
            error = evt.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure()
            return
        new_value = evt.attr_value.value
        self._component_manager.update_device_dish_mode(new_value)
        self._logger.info(f"DishMode value updated to {new_value}")
