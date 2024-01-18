"""Class for managing dish kvalue validation during
initialization/restart of device
"""
# pylint: disable=no-value-for-parameter
import time

from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue


class DishkValueValidationManager:
    """Class dish vkvalue validation during initialization/restart"""

    def __init__(self, component_manager, logger) -> None:
        self.component_manager = component_manager
        self.logger = logger
        self.dish_manager_kvalue = ""

    def is_dish_manager_ready(self):
        """Wait and check if csp manager is ready"""
        count = 0
        setkvalue_obj = SetKValue(self.component_manager, self.logger)
        while count < self.component_manager.dish_availability_check_timeout:
            try:
                self.component_manager.check_device_responsive()
                result_code, _ = setkvalue_obj.init_adapter()
                if result_code == ResultCode.OK:
                    self.dish_manager_kvalue = setkvalue_obj.dish_master_adapter._proxy.kValue
                    return True
            except Exception as e:
                self.logger.exception("Dish manager is unresponsive %s", e)
            count += 3
            time.sleep(3)
        return False

    def get_dish_manager_kvalue(self) -> int:
        """Get kValue attribute value of dish manager"""
        return self.dish_manager_kvalue

    def get_dish_ln_memorized_kvalue(self) -> str:
        """Return memorized kvalue dish leaf node"""
        return self.component_manager.kValue

    def validate_dish_kvalue(self):
        """Validate kvalue of dish leaf node and dish manager"""
        dish_manager_kvalue = self.get_dish_manager_kvalue()
        dish_ln_kvalue = self.get_dish_ln_memorized_kvalue()
        self.logger.info("Dish Manager k-value: %s", dish_manager_kvalue)
        self.logger.info("Dish Leaf Node k-value: %s", dish_ln_kvalue)

        if not dish_manager_kvalue or not dish_ln_kvalue:
            self.logger.info("kvalue not set")
            self.component_manager.kValueValidationResult = ResultCode.UNKNOWN
            if self.component_manager.kvalue_validation_callback:
                self.component_manager.kvalue_validation_callback()

        elif dish_manager_kvalue == dish_ln_kvalue:
            self.logger.info("kvalues are identical on dish manager and dln.")
            self.component_manager.kValueValidationResult = ResultCode.OK
            if self.component_manager.kvalue_validation_callback:
                self.component_manager.kvalue_validation_callback()
        else:
            self.logger.info("kvalue not identical on dish manager and dln.")
            self.component_manager.kValueValidationResult = ResultCode.FAILED
            if self.component_manager.kvalue_validation_callback:
                self.component_manager.kvalue_validation_callback()
