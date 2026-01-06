# flake8: noqa=E501
"""
Dataclass representing inputs used by the rule engine to evaluate health state.
"""
import threading
from dataclasses import asdict, dataclass, field

# from multiprocessing import context
from typing import Dict, List, Optional

from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tmc_common import Band

from ska_tmc_dishleafnode.enums import CapabilityStates
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

    result_code: str = field(default=ResultCode.STARTED.name)


@dataclass
class DishManagerHealthData:
    """
    Context object for Dish Manager health data.
    """

    health_state: HealthState = field(default=HealthState.UNKNOWN)


@dataclass
class DishBandCapabilityStateData:
    """
    Context object for Dish Band Capability States.
    """

    band_capabilities: Dict[str, CapabilityStates] = field(
        default_factory=lambda: {
            "B1": CapabilityStates.UNKNOWN.name,
            "B2": CapabilityStates.UNKNOWN.name,
            "B3": CapabilityStates.UNKNOWN.name,
            "B4": CapabilityStates.UNKNOWN.name,
            "B5a": CapabilityStates.UNKNOWN.name,
            "B5b": CapabilityStates.UNKNOWN.name,
        }
    )


@dataclass
class DishHealthData:
    """
    Context object passed to health rule engine.

    Extend this dataclass when new health inputs
    (PTT, GPM, etc.) are added.
    """

    receiver_band: Band = Band.NONE

    gpm_validation_result: GPMValidationResultData = field(
        default_factory=GPMValidationResultData
    )
    dish_manager_health_data: DishManagerHealthData = field(
        default_factory=DishManagerHealthData
    )
    k_value_validation_result: KValueValidationResultData = field(
        default_factory=KValueValidationResultData
    )
    band_capability_data: DishBandCapabilityStateData = field(
        default_factory=DishBandCapabilityStateData
    )


class HealthManager:
    """
    Manager for Dish Leaf Node health data.
    """

    def __init__(self, component_manager, logger):
        self.health_data = DishHealthData()
        self.component_manager = component_manager
        self.logger = logger

        self.eventlock = threading._RLock()

    def update_health_data_and_aggregate(self, data, datatype) -> None:
        """
        Update health data from component manager.
        """
        # figure out which data to update

        with self.eventlock:
            match datatype:
                case "GPMValidationResultData":
                    self.health_data.gpm_validation_result = (
                        GPMValidationResultData(result=data)
                    )
                    self.logger.debug(
                        "Updated GPMValidationResultData in health data: %s",
                        str(self.health_data),
                    )
                case "KValueValidationResultData":
                    self.health_data.k_value_validation_result = (
                        KValueValidationResultData(result_code=data)
                    )
                    self.logger.debug(
                        "Updated KValueValidationResultData in"
                        " health data: %s",
                        str(self.health_data),
                    )
                case "DishManagerHealthData":
                    self.health_data.dish_manager_health_data = (
                        DishManagerHealthData(health_state=data)
                    )
                    self.logger.debug(
                        "Updated DishManagerHealthData in health data: %s",
                        str(self.health_data),
                    )
                    return  # not contributing to health state evaluation
                case "DishBandCapabilityStateData":
                    band_name, capability_state = data
                    self.health_data.band_capability_data.band_capabilities[
                        band_name
                    ] = capability_state
                    self.logger.debug(
                        "Updated DishBandCapabilityStateData"
                        " in health data: %s",
                        str(self.health_data),
                    )
                case "receiver_band":
                    if isinstance(data, Band):
                        self.health_data.receiver_band = data
                    else:
                        self.health_data.receiver_band = Band(data)

                    self.logger.debug(
                        "Updated receiver_band in health data: %s",
                        self.health_data.receiver_band,
                    )

                case _:
                    self.logger.warning("Unknown datatype: %s", datatype)

        health_state = self.evaluate_health_state(self.health_data)
        self.logger.debug(
            "Evaluated health state: %s for data: %s",
            str(health_state),
            str(self.health_data),
        )
        if health_state is None:
            self.logger.debug("Healthstate returned as None, skipping update")
            return

        health_info = self.generate_health_info(self.health_data)
        self.logger.debug("Generated health info: %s", str(health_info))

        if self.component_manager._update_health_info_callback:
            self.component_manager._update_health_info_callback(health_info)

        if self.component_manager._update_health_state_callback:
            self.component_manager._update_health_state_callback(health_state)

    def evaluate_health_state(
        self, health_context: DishHealthData
    ) -> Optional[HealthState]:
        """
        Evaluate health state using rules.

        Args:
            context: DishHealthData

        Returns:
            HealthState or None if no rule matched
        """

        def sanitize_for_rules(obj):
            import enum

            if isinstance(obj, enum.Enum):
                return obj.name
            if isinstance(obj, dict):
                return {k: sanitize_for_rules(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize_for_rules(v) for v in obj]
            if obj is None:
                return []
            return obj

        self.logger.info(
            "Health rules matched for context: %s", health_context
        )

        context_dict = sanitize_for_rules(asdict(health_context))

        band_caps = context_dict["band_capability_data"]["band_capabilities"]

        context_dict["band_capability_data"]["band_capability_values"] = set(
            band_caps.values()
        )

        self.logger.info("Health rules matched for context: %s", context_dict)

        for health_state, rules in HEALTH_RULES.items():
            self.logger.info("Rule match for  %s", rules)

            if any(rule.matches(context_dict) for rule in rules):
                self.logger.info("HealthState decided as %s", health_state)
                return health_state

        self.logger.debug(
            "No health rule matched for context: %s", health_context
        )
        return None
        return None

    def generate_health_info(self, health_context: DishHealthData) -> Dict:
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
        dish_device_name = self.component_manager.dish_dev_name
        dish_name = (
            "mid-tmc/leaf-node-dish/ska001"  # Placeholder for actual dish name
        )
        health_info: Dict = {"HealthSummary": {}}
        health_info["HealthSummary"][dish_name] = {"Info": []}

        good_states = {
            "STANDBY",
            "CONFIGURING",
            "OPERATE_FULL",
            "OPERATE_DEGRADED",
            "UNKNOWN",
        }
        requested_band = health_context.receiver_band.name

        if health_context.receiver_band not in (Band.NONE, Band.UNKNOWN):
            band_state = (
                health_context.band_capability_data.band_capabilities.get(
                    requested_band, CapabilityStates.UNKNOWN
                )
            )
            if band_state.name not in good_states:
                health_info["HealthSummary"][dish_name]["Info"].append(
                    f"requested band {requested_band} is {band_state.name}"
                    + " — not fully available for observation."
                )
            # Do NOT report other bands when one is configured
        else:
            # list bad bands
            bad_bands = [
                name
                for name, state in (
                    health_context.band_capability_data.band_capabilities.items()
                )
                if state.name not in good_states
            ]
            if bad_bands:
                health_info["HealthSummary"][dish_name]["Info"].append(
                    f"Unavailable bands: {', '.join(bad_bands)}."
                )

        # Check GPM validation results for errors
        for idx, result in enumerate(
            health_context.gpm_validation_result.result
        ):
            if result == "FAILED":
                error_msg = f"GPM validation failed for GPM index {idx}."
                health_info["HealthSummary"][dish_name]["Info"].append(
                    error_msg
                )
        # Check KValue validation results for errors
        if (
            health_context.k_value_validation_result.result_code
            != ResultCode.OK.name
        ):
            error_msg = "KValue validation failed."
            health_info["HealthSummary"][dish_name]["Info"].append(error_msg)
        # Check Dish Manager health state for errors
        if health_context.dish_manager_health_data.health_state in [
            HealthState.DEGRADED,
            HealthState.FAILED,
            HealthState.UNKNOWN,
        ]:
            error_msg = (
                f"Dish Manager {dish_device_name}"
                + " health state reported "
                + f"as {health_context.dish_manager_health_data.health_state.name}."
            )
            health_info["HealthSummary"][dish_name]["Info"].append(error_msg)
        return health_info
        return health_info
