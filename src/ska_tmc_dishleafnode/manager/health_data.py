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
class GPMValidationResultData:
    """
    Context object for GPM validation results.
    """

    result: List[str] = field(default_factory=list)


@dataclass
class KValueValidationResultData:
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

    gpm_validation_result: GPMValidationResultData = field(
        default_factory=GPMValidationResultData
    )
    # k_value_validation_result: KValueValidationResultData = field(
    #     default_factory=KValueValidationResultData
    # )


class HealthManager:
    """
    Manager for Dish Leaf Node health data.
    """

    def __init__(self, component_manager, logger):
        self.health_data = DishHealthData()
        self.component_manager = component_manager
        self.logger = logger

        self.attribute_mapping: Dict[str, str] = {
            "GPMValidationResultData": "gpm_validation_result",
            "KValueValidationResultData": "k_value_validation_result",
        }

        self.eventlock = threading._RLock()

    def update_health_data(self, data, datatype) -> None:
        """
        Update health data from component manager.
        """
        # figure out which data to update

        with self.eventlock:
            if datatype == "GPMValidationResultData":
                self.health_data.gpm_validation_result = (
                    GPMValidationResultData(result=data)
                )
                self.logger.debug(
                    "Updated GPMValidationResultData in health data: %s",
                    str(self.health_data),
                )
            elif datatype == "KValueValidationResultData":
                # self.health_data.k_value_validation_result = (
                #     KValueValidationResultData(result_code=data)
                # )
                self.logger.debug(
                    "Updated KValueValidationResultData in health data: %s",
                    str(self.health_data),
                )
        current_health_state_data = copy.deepcopy(self.health_data)
        health_state = self.evaluate_health_state(current_health_state_data)
        self.logger.debug(
            "Evaluated health state: %s for data: %s",
            str(health_state),
            str(current_health_state_data),
        )
        if health_state is None:
            return

        if health_state == HealthState.DEGRADED:
            health_info = self.generate_health_info(
                health_state, current_health_state_data
            )
            self.logger.debug("Generated health info: %s", str(health_info))
            if self.component_manager._update_health_info_callback:
                self.component_manager._update_health_info_callback(
                    health_info
                )

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

    def generate_health_info(
        self, health_state: HealthState, context: DishHealthData
    ) -> Dict:
        """
        Generate health info dictionary based on health state and context.

        example:
        {
            "HealthSummary": {
                "mid-tmc/leaf-node-dish/ska036": {
                    "Info": [
                        "Dish is configured for Band\
                        1 but Band1 is not available",
                        "another error",
                        "another error"
                    ]
                }
            }
        }

        Args:
            health_state: HealthState
            context: DishHealthData
        Returns:
            Dict containing health info
        """
        health_info: Dict = {"HealthSummary": {}}
        dish_name = (
            "mid-tmc/leaf-node-dish/ska001"  # Placeholder for actual dish name
        )
        health_info["HealthSummary"][dish_name] = {"Info": []}

        if health_state == HealthState.DEGRADED:
            # Check GPM validation results for errors
            for idx, result in enumerate(context.gpm_validation_result.result):
                if result == "FAILED":
                    error_msg = f"GPM validation failed for GPM index {idx}."
                    health_info["HealthSummary"][dish_name]["Info"].append(
                        error_msg
                    )

        # Additional health state checks can be added here

        return health_info
