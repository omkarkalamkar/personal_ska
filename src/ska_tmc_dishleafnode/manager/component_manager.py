"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
# pylint: disable=abstract-method
from ska_tmc_common.command_executor import CommandExecutor
from ska_tmc_common.event_receiver import EventReceiver
from ska_tmc_common.liveliness_probe import LivelinessProbe
from ska_tmc_common.tmc_component_manager import TmcLeafNodeComponentManager


class DishLNComponentManager(TmcLeafNodeComponentManager):
    """
    A component manager for The Dish Leaf Node component.
    """

    # pylint: disable=unused-argument,line-too-long
    def __init__(
        self,
        dish_dev_name,
        op_state_model,
        logger=None,
        update_device_callback=None,
        update_command_in_progress_callback=None,
        liveliness_probe=True,
        event_receiver=True,
        max_workers=5,
        proxy_timeout=500,
        sleep_time=1,
        timeout=30,
    ):
        """
        Initialise a new ComponentManager instance.

        :param op_state_model: the op state model used by this component
            manager
        :param logger: a logger for this component manager
        :param liveliness_probe: allows enabling/disabling the
            liveliness probe;
        :param event_receiver: allows eanabling/disabling the event subscriber;
        :param max_workers: allows to specify number of threads to be used by
        the liveliness probe;
        :param proxy_timeout: allows to specify a client side timeout for
        sub-devices in milliseconds used by the liveliness probe;
        :param sleep_time: allows to specify the wait between each iteration
        of the liveliness probe and EventSubscriber;
        """
        super().__init__(
            op_state_model,
            logger,
            liveliness_probe,
            event_receiver,
            max_workers,
            proxy_timeout,
            sleep_time,
        )

        self._liveliness_probe = None
        if liveliness_probe:
            self._liveliness_probe = LivelinessProbe(
                self, logger, max_workers, proxy_timeout, sleep_time
            )
            self._liveliness_probe.start()
        else:
            logger.warning("Liveliness probe is not running")

        self._event_receiver = None
        if event_receiver:
            self._event_receiver = EventReceiver(
                self, logger, max_workers, proxy_timeout, sleep_time
            )
            self._event_receiver.start()
        else:
            logger.warning("Event reciever is not running")

        self.command_executor = CommandExecutor(
            logger,
            _update_command_in_progress_callback=update_command_in_progress_callback,  # noqa: E501
        )

        self.timeout = timeout
        self.dish_dev_name = dish_dev_name
