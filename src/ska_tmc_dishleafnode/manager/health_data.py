"""
Dataclass representing inputs used by the rule engine to evaluate health state.
"""
import threading
from dataclasses import asdict, dataclass, field
from enum import Enum
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

    result_code: ResultCode = field(default=ResultCode.STARTED)


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
            "B1": CapabilityStates.UNKNOWN,
            "B2": CapabilityStates.UNKNOWN,
            "B3": CapabilityStates.UNKNOWN,
            "B4": CapabilityStates.UNKNOWN,
            "B5a": CapabilityStates.UNKNOWN,
            "B5b": CapabilityStates.UNKNOWN,
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

    _active_issues: Dict[str, str]

    def __init__(self, component_manager, logger):
        self.health_data = DishHealthData()
        self.component_manager = component_manager
        self.logger = logger

        self.eventlock = threading.RLock()

        self._active_issues: Dict[str, str] = {}
        self._cached_health_info: Optional[Dict] = None
        self._cached_health_state: Optional[HealthState] = None

    def update_health_data_and_aggregate(self, data, datatype) -> None:
        """
        Update health data from component manager.
        """
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
                    self._update_gpm_issues()
                case "KValueValidationResultData":
                    if not isinstance(data, ResultCode):
                        data = ResultCode(data)
                    self.health_data.k_value_validation_result = (
                        KValueValidationResultData(result_code=data)
                    )
                    self.logger.debug(
                        "Updated KValueValidationResultData in"
                        " health data: %s",
                        str(self.health_data),
                    )
                    self._update_kvalue_issues()
                case "DishManagerHealthData":
                    if not isinstance(data, HealthState):
                        data = HealthState(data)
                    self.health_data.dish_manager_health_data = (
                        DishManagerHealthData(health_state=data)
                    )
                    self.logger.debug(
                        "Updated DishManagerHealthData in health data: %s",
                        str(self.health_data),
                    )
                    self._update_dishmanager_issues()
                case "DishBandCapabilityStateData":
                    self.logger.info(
                        "Updating DishBandCapabilityStateData as %s", data
                    )
                    band_name, capability_state = data
                    if not isinstance(capability_state, CapabilityStates):
                        capability_state = CapabilityStates(capability_state)
                    self.health_data.band_capability_data.band_capabilities[
                        band_name
                    ] = capability_state
                    self.logger.info(
                        "Updated DishBandCapabilityStateData"
                        " in health data: %s",
                        str(self.health_data),
                    )
                    self._update_band_issues()
                case "receiver_band":
                    if isinstance(data, Band):
                        self.health_data.receiver_band = data
                    else:
                        self.health_data.receiver_band = Band(data)

                    self.logger.debug(
                        "Updated receiver_band in health data: %s",
                        self.health_data.receiver_band,
                    )
                    self._update_band_issues()
                case _:
                    self.logger.warning("Unknown datatype: %s", datatype)

            health_state = self.evaluate_health_state(self.health_data)
            self.logger.debug(
                "Evaluated health state: %s for data: %s",
                str(health_state),
                str(self.health_data),
            )

            health_info = self.generate_health_info()

            info_changed = health_info != self._cached_health_info
            state_changed = health_state != self._cached_health_state

            if info_changed:
                self._cached_health_info = health_info
                if self.component_manager._update_health_info_callback:
                    self.component_manager._update_health_info_callback(
                        health_info
                    )

            if state_changed or info_changed:
                self._cached_health_state = health_state
                if self.component_manager._update_health_state_callback:
                    self.component_manager._update_health_state_callback(
                        health_state
                    )

    def _update_band_issues(self):
        """
        Update band-related issues in active issues.
        """

        self.logger.info("Updating band issues")

        good_states = {
            "STANDBY",
            "CONFIGURING",
            "OPERATE_FULL",
            "OPERATE_DEGRADED",
            "UNKNOWN",
        }
        requested = self.health_data.receiver_band
        self.logger.info("Requested band: %s", requested)

        self.logger.info("Active issues: %s", self._active_issues)

        # Clear old band-related issues
        keys_to_remove = [
            k for k in self._active_issues if k.startswith("band_")
        ]
        for k in keys_to_remove:
            self._active_issues.pop(k, None)

        self.logger.info(
            "Active issues after removal: %s", self._active_issues
        )

        self.logger.info("requested.name    %s", requested.name)

        if requested not in (Band.NONE, Band.UNKNOWN):
            state = (
                self.health_data.band_capability_data.band_capabilities.get(
                    requested.name,
                    CapabilityStates.UNKNOWN,
                )
            )

            self.logger.info("state - %s", state)
            self.logger.info("state.value - %s", state.value)
            self.logger.info("state.name- %s", state.name)
            if state.name not in good_states:
                self._active_issues[f"band_requested_{requested.name}"] = (
                    f"requested band {requested.name} is {state.value} not "
                    + "fully available for observation."
                )
        else:
            band_capabilities = (
                self.health_data.band_capability_data.band_capabilities.items()
            )
            self.logger.info("Band capabilities: %s", band_capabilities)
            bad_bands = [
                name
                for name, state in band_capabilities
                if state.name not in good_states
            ]
            self.logger.info("Bad bands: %s", bad_bands)
            if bad_bands:
                self._active_issues[
                    "band_unavailable"
                ] = f"Unavailable bands: {', '.join(bad_bands)}."
            self.logger.info("Updated active issues: %s", self._active_issues)

    def _update_gpm_issues(self):
        """
        Update GPM-related issues in active issues.
        """
        # Clear old GPM-related issues
        keys_to_remove = [
            k for k in self._active_issues if k.startswith("gpm_")
        ]
        for k in keys_to_remove:
            self._active_issues.pop(k, None)

        for idx, result in enumerate(
            self.health_data.gpm_validation_result.result
        ):
            if result == ResultCode.FAILED:
                error_msg = f"GPM validation failed for GPM index {idx}."
                self._active_issues[f"gpm_{idx}"] = error_msg

    def _update_kvalue_issues(self):
        """
        Update KValue-related issues in active issues.
        """
        # Clear old KValue-related issues
        keys_to_remove = [
            k for k in self._active_issues if k.startswith("kvalue_")
        ]
        for k in keys_to_remove:
            self._active_issues.pop(k, None)

        if (
            self.health_data.k_value_validation_result.result_code
            != ResultCode.OK
        ):
            error_msg = "KValue validation failed."
            self._active_issues["kvalue_failed"] = error_msg

    def _update_dishmanager_issues(self):
        """
        Update DishManager-related issues in active issues.
        """
        # Clear old DishManager-related issues
        keys_to_remove = [
            k for k in self._active_issues if k.startswith("dishmanager_")
        ]
        for k in keys_to_remove:
            self._active_issues.pop(k, None)

        if self.health_data.dish_manager_health_data.health_state in [
            HealthState.DEGRADED,
            HealthState.FAILED,
            HealthState.UNKNOWN,
        ]:
            health_state_name = (
                self.health_data.dish_manager_health_data.health_state.name
            )
            dish_device_name = self.component_manager.dish_dev_name
            error_msg = (
                f"Dish Manager {dish_device_name} health state reported as "
                + f"{health_state_name}."
            )
            self._active_issues["dishmanager_health"] = error_msg

    def evaluate_health_state(
        self, health_context: DishHealthData
    ) -> HealthState:
        """
        Evaluate health state using rules.

        Args:
            health_context: DishHealthData

        Returns:
            HealthState (never None now)
        """

        # def sanitize_for_rules(obj):
        #     if isinstance(obj, Enum):
        #         return obj.name
        #     if isinstance(obj, (dict, list, set, tuple)):
        #         container = type(obj)
        #         return container(sanitize_for_rules(v) for v in obj)
        #     return obj

        def sanitize_for_rules(obj):
            if isinstance(obj, Enum):  # Proper Enum check
                return obj.name
            if isinstance(obj, dict):
                return {k: sanitize_for_rules(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize_for_rules(v) for v in obj]
            if isinstance(obj, set):
                return {sanitize_for_rules(v) for v in obj}
            return obj

        context_dict = sanitize_for_rules(asdict(health_context))

        # Expose the set of current capability states for rules (now strs)
        band_caps = context_dict["band_capability_data"]["band_capabilities"]
        context_dict["band_capability_data"]["band_capability_values"] = set(
            band_caps.values()
        )

        self.logger.debug(
            "Evaluating health state with context: %s", context_dict
        )

        # Evaluate in priority order: OK > DEGRADED > FAILED > UNKNOWN
        for health_state in (
            HealthState.OK,
            HealthState.DEGRADED,
            HealthState.FAILED,
            HealthState.UNKNOWN,
        ):
            for rule in HEALTH_RULES.get(health_state, []):
                if rule.matches(context_dict):
                    self.logger.debug(
                        "HealthState decided as %s", health_state.name
                    )
                    return health_state

        # Unreachable due to UNKNOWN fallback, but log
        self.logger.warning(
            "Unexpected: No rule matched, defaulting to UNKNOWN"
        )
        return HealthState.UNKNOWN

    def generate_health_info(self) -> Dict:
        """
        Generate health info dictionary from active issues.

        Returns:
            Dict containing health info
        """
        dish_name = (
            # Placeholder for actual dish name
            "mid-tmc/leaf-node-dish/ska001"
        )
        health_info: Dict = {"HealthSummary": {}}
        health_info["HealthSummary"][dish_name] = {
            "Info": list(self._active_issues.values())
        }
        return health_info
