"""Class for managing dish kvalue validation during
initialization/restart of device
"""
# pylint: disable=no-value-for-parameter
from __future__ import annotations

import threading
import time

from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue


class DishkValueValidationManager:
    """Class for dish kValue validation during dish
    leaf node initialization/restart
    """

    def __init__(
        self: DishkValueValidationManager, component_manager, logger
    ) -> None:
        self.component_manager = component_manager
        self.logger = logger
        self.dish_manager_kvalue = ""
        self.kvalue_validation_lock = threading.Lock()

    def is_dish_manager_ready(self: DishkValueValidationManager) -> bool:
        """Wait and check if dish manager is ready

        :return: bool
        """
        exception = ""
        count = 0
        setkvalue_obj = SetKValue(self.component_manager, self.logger)
        while count < self.component_manager.dish_availability_check_timeout:
            try:
                self.component_manager.check_device_responsive()
                result_code, _ = setkvalue_obj.init_adapter()
                if result_code == ResultCode.OK:
                    self.dish_manager_kvalue = (
                        setkvalue_obj.dish_master_adapter.kValue
                    )
                    return True
            except Exception as e:
                exception = str(e)
            count += 1
            time.sleep(1)
        if exception:
            self.logger.exception(
                "Dish manager is unresponsive , Exception: %s", str(exception)
            )
        return False

    def get_dish_manager_kvalue(self: DishkValueValidationManager) -> int:
        """Get kValue attribute value of dish manager

        :return: int
        """
        return self.dish_manager_kvalue

    def get_dish_ln_memorized_kvalue(self: DishkValueValidationManager) -> int:
        """Return memorized kvalue dish leaf node

        :return: int
        """
        return self.component_manager.kValue

    def validate_dish_kvalue(self: DishkValueValidationManager) -> None:
        """Validate kvalue of dish leaf node and dish manager

        :return: None
        """
        dish_manager_kvalue = self.get_dish_manager_kvalue()
        dish_ln_kvalue = self.get_dish_ln_memorized_kvalue()
        self.logger.info("Dish Manager k-value: %s", dish_manager_kvalue)
        self.logger.info("Dish Leaf Node k-value: %s", dish_ln_kvalue)
        with self.kvalue_validation_lock:
            self.kvalue_validation_update(dish_manager_kvalue, dish_ln_kvalue)

    def validate_dish_kvalue_from_event(
        self: DishkValueValidationManager, kvalue: int
    ) -> None:
        """Validate kvalue of dish leaf node and dish manager from event
        :return: None
        """
        dish_ln_kvalue = self.get_dish_ln_memorized_kvalue()
        with self.kvalue_validation_lock:
            self.kvalue_validation_update(dish_ln_kvalue, kvalue)

    def kvalue_validation_update(
        self: DishkValueValidationManager,
        dish_manager_kvalue: str,
        dish_ln_kvalue: str,
    ) -> None:
        """Update kValueValidationResult attribute of dish leaf node

        :param result: kValue validation result
        :return: None
        """
        if not dish_manager_kvalue or not dish_ln_kvalue:
            if (
                self.component_manager.kValueValidationResult
                == ResultCode.UNKNOWN
            ):
                return
            self.logger.debug("kValue not set")
            self.component_manager.kValueValidationResult = ResultCode.UNKNOWN
            if self.component_manager.kvalue_validation_callback:
                self.component_manager.kvalue_validation_callback()
        elif dish_manager_kvalue == dish_ln_kvalue:
            if self.component_manager.kValueValidationResult == ResultCode.OK:
                return
            self.logger.info(
                "kValues are identical on dish manager and dish leaf node."
            )
            self.component_manager.kValueValidationResult = ResultCode.OK
            if self.component_manager.kvalue_validation_callback:
                self.component_manager.kvalue_validation_callback()
        else:
            if (
                self.component_manager.kValueValidationResult
                == ResultCode.FAILED
            ):
                return

            self.logger.error(
                "kValue not identical on dish manager and dish leaf node."
            )
            self.component_manager.kValueValidationResult = ResultCode.FAILED
            if self.component_manager.kvalue_validation_callback:
                self.component_manager.kvalue_validation_callback()
