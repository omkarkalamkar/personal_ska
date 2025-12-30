"""
Dataclass representing inputs used by the rule engine to evaluate health state.
"""

import copy
import threading
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.manager.health_rules import HEALTH_RULES


@dataclass
class GPMValidationResult:
    """
    Context object for GPM validation results.
    """

    result: List[str] = field(default_factory=list)


@dataclass
class KValueValidationResult:
    """
    Context object for kValue validation result.
    """

    result_code: ResultCode = field(default=ResultCode.UNKNOWN)


@dataclass
class DishHealthData:
    """
    Context object passed to health rule engine.

    Extend this dataclass when new health inputs
    (PTT, GPM, etc.) are added.
    """

    gpm_validation_result: GPMValidationResult = field(
        default_factory=GPMValidationResult
    )
    k_value_validation_result: KValueValidationResult = field(
        default_factory=KValueValidationResult
    )


class HealthManager:
    """
    Manager for Dish Leaf Node health data.
    """

    def __init__(self, component_manager, logger):
        self.health_data = DishHealthData()
        self.component_manager = component_manager
        self.logger = logger

        self.attribute_mapping: Dict[str, str] = {
            "GPMValidationResult": "gpm_validation_result",
            "KValueValidationResult": "k_value_validation_result",
        }

        self.eventlock = threading._RLock()

    def update_health_data(self, data, datatype) -> None:
        """
        Update health data from component manager.
        """
        # figure out which data to update

        with self.eventlock:
            if datatype == "GPMValidationResult":
                self.health_data.gpm_validation_result = GPMValidationResult(
                    result=data
                )
                self.logger.debug(
                    "Updated GPMValidationResult in health data: %s",
                    str(self.health_data),
                )
            elif datatype == "KValueValidationResult":
                self.health_data.k_value_validation_result = (
                    KValueValidationResult(result_code=data)
                )
                self.logger.debug(
                    "Updated KValueValidationResult in health data: %s",
                    str(self.health_data),
                )
        current_health_state_data = copy.deepcopy(self.health_data)
        health_state = self.evaluate_health_state(current_health_state_data)
        if health_state is None:
            return

        if self.component_manager._update_health_state_callback:
            self.component_manager._update_health_state_callback(health_state)

    def evaluate_health_state(
        self, context: DishHealthData
    ) -> Optional[HealthState]:
        """
        Evaluate health state using rules.

        Args:
            context: DishHealthData

        Returns:
            HealthState or None if no rule matched
        """

        for health_state, rules in HEALTH_RULES.items():
            if any(rule.matches(asdict(context)) for rule in rules):
                self.logger.info("HealthState decided as %s", health_state)
                return health_state

        self.logger.debug("No health rule matched for context: %s", context)
        return None
