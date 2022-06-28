"""
This module provides an implementation of the Dish Leaf Node ComponentManager.
"""
# pylint: disable=abstract-method
from ska_tmc_common.command_executor import CommandExecutor
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
        monitoring_loop=False,
        event_receiver=False,
        max_workers=5,
        proxy_timeout=500,
        sleep_time=1,
        time_out=30,
    ):
        """
        Initialise a new ComponentManager instance.

        :param op_state_model: the op state model used by this component
            manager
        :param logger: a logger for this component manager
        :param monitoring_loop: allows eanabling/disabling the monitoring loop;
        For DishLN monitoring loop is not required. Therefore this parameter
        will always be False.
        :param event_receiver: allows eanabling/disabling the event subscriber;
        For DishLN event receiver is not required. Therefore this parameter
        will always be False.
        :param max_workers: allows to specify number of threads to be used by
        the monitoring loop;
        This parameter is not used for DishLN.
        :param proxy_timeout: allows to specify a client side timeout for
        sub-devices in milliseconds
        used by the monitoring loop; This parameter is not used for DishLN.
        :param sleep_time: allows to specify the wait between each iteration
        of the monitoring loop and EventSubscriber;
        """
        super().__init__(
            op_state_model,
            logger,
            monitoring_loop,
            event_receiver,
            max_workers,
            proxy_timeout,
            sleep_time,
        )

        self.command_executor = CommandExecutor(
            logger,
            _update_command_in_progress_callback=update_command_in_progress_callback,  # noqa: E501
        )
        self.time_out = time_out
        self.dish_dev_name = dish_dev_name
