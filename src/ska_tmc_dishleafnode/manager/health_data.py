"""
Dataclass representing inputs used by the rule engine to evaluate health state.
"""
import threading
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from unittest import result

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


class DishHealthStateAndInfoManager:
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
        Update health data from component manager and trigger aggregation.
        """
        with self.eventlock:
            match datatype:
                case "GPMValidationResultData":
                    self._update_gpm_validation(data)
                case "KValueValidationResultData":
                    self._update_kvalue_validation(data)
                case "DishManagerHealthData":
                    self._update_dish_manager_health(data)
                case "DishBandCapabilityStateData":
                    self._update_band_capability(data)
                case "receiver_band":
                    self._update_receiver_band(data)
                case _:
                    self.logger.warning("Unknown datatype: %s", datatype)
                    return

            # After any successful update → re-evaluate
            health_state = self.evaluate_health_state(self.health_data)
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

    def _update_gpm_validation(self, data: List[str]) -> None:
        """Update GPM validation result and related issues."""
        self.health_data.gpm_validation_result = GPMValidationResultData(
            result=data
        )
        self.logger.debug(
            "Updated GPMValidationResultData: %s", str(self.health_data)
        )
        self._update_gpm_issues()

    def _update_kvalue_validation(self, data) -> None:
        """Update K-value validation result and related issues."""
        if not isinstance(data, ResultCode):
            data = ResultCode(data)

        self.health_data.k_value_validation_result = (
            KValueValidationResultData(result_code=data)
        )
        self.logger.debug(
            "Updated KValueValidationResultData: %s", str(self.health_data)
        )
        self._update_kvalue_issues()

    def _update_dish_manager_health(self, data) -> None:
        """Update Dish Manager health state and related issues."""
        if not isinstance(data, HealthState):
            data = HealthState(data)

        self.health_data.dish_manager_health_data = DishManagerHealthData(
            health_state=data
        )
        self.logger.debug(
            "Updated DishManagerHealthData: %s", str(self.health_data)
        )
        self._update_dishmanager_issues()

    def _update_band_capability(self, data) -> None:
        """Update single band capability state and related issues."""
        self.logger.info("Updating DishBandCapabilityStateData as %s", data)
        band_name, capability_state = data

        if not isinstance(capability_state, CapabilityStates):
            capability_state = CapabilityStates(capability_state)

        self.health_data.band_capability_data.band_capabilities[
            band_name
        ] = capability_state
        self.logger.info("Updated band capability → %s", str(self.health_data))

        self._update_band_issues()

    def _update_receiver_band(self, data) -> None:
        """Update current receiver band and
        trigger band-related issue check."""

        if isinstance(data, Band):
            self.health_data.receiver_band = data
        else:
            self.health_data.receiver_band = Band(data)

        self.logger.debug(
            "Updated receiver_band: %s", self.health_data.receiver_band
        )
        self._update_band_issues()

    def _update_band_issues(self) -> None:
        """
        Update band-related issues in _active_issues
        based on current receiver band and capability states.
        """
        self.logger.debug("Updating band issues")

        good_states = {
            "STANDBY",
            "CONFIGURING",
            "OPERATE_FULL",
            "OPERATE_DEGRADED",
            "UNKNOWN",
        }

        requested = self.health_data.receiver_band

        band_capabilities = (
            self.health_data.band_capability_data.band_capabilities
        )
        any_bad_state = any(
            state.name not in good_states
            for state in band_capabilities.values()
        )

        if requested in (Band.NONE, Band.UNKNOWN) and not any_bad_state:
            self.logger.debug(
                "No requested band and all bands are in good state "
                "→ clearing band issues"
            )
            self._clear_band_issues()
            return

        # Clear previous band-related issues
        self._clear_band_issues()

        if requested not in (Band.NONE, Band.UNKNOWN):
            state = band_capabilities.get(
                requested.name, CapabilityStates.UNKNOWN
            )

            if state.name not in good_states:
                msg = (
                    f"Requested band {requested.name} is in state "
                    f"{state.name} (not fully available)"
                )
                self._active_issues[f"band_requested_{requested.name}"] = msg
                self.logger.info(msg)
            else:
                self.logger.debug(
                    "Requested band %s is in acceptable state: %s",
                    requested.name,
                    state.name,
                )

        else:
            # No specific band requested → check if any band is bad
            bad_bands = [
                name
                for name, state in band_capabilities.items()
                if state.name not in good_states
            ]

            if bad_bands:
                msg = f"Unavailable bands: {', '.join(bad_bands)}"
                self._active_issues["band_unavailable"] = msg
                self.logger.info(msg)
            else:
                self.logger.debug(
                    "No specific band requested and all bands are healthy"
                )

        if self._active_issues:
            self.logger.debug(
                "Active band-related issues after update: %s",
                {
                    k: v
                    for k, v in self._active_issues.items()
                    if k.startswith("band_")
                },
            )
        else:
            self.logger.debug("No active band-related issues after update")

    def _clear_band_issues(self) -> None:
        """Helper to remove all previous band-related issues."""
        removed = [
            k for k in list(self._active_issues) if k.startswith("band_")
        ]
        for key in removed:
            self._active_issues.pop(key, None)

        if removed:
            self.logger.debug(
                "Cleared %d previous band-related issue(s)", len(removed)
            )

    def _update_gpm_issues(self) -> None:
        """
        Update GPM-related issues in active issues.
        """

        def normalize_result(result_val):
            if isinstance(result_val, ResultCode):
                return result_val.name.upper()
            if isinstance(result_val, int):
                try:
                    return ResultCode(result_val).name.upper()
                except ValueError:
                    return str(result_val).upper()
            if isinstance(result_val, str):
                return result_val.upper()
            return str(result_val).upper()

        # Clear old GPM-related issues
        keys_to_remove = [
            k for k in self._active_issues if k.startswith("gpm_")
        ]
        for k in keys_to_remove:
            self._active_issues.pop(k, None)

        for idx, result_val in enumerate(
            self.health_data.gpm_validation_result.result
        ):
            self.logger.debug(
                "Evaluating GPM result at index %d: %s", idx, result
            )

            res = normalize_result(result_val)

            if res == "FAILED":
                self._active_issues[
                    f"gpm_{idx}"
                ] = f"GPM validation failed for GPM index {idx}."
            elif res == "DEGRADED":
                self._active_issues[
                    f"gpm_{idx}"
                ] = f"GPM validation degraded for GPM index {idx}."

            # if (
            #     (
            #         isinstance(result, ResultCode)
            #         and result == ResultCode.FAILED
            #     )
            #     or (
            #         isinstance(result, int)
            #         and result == ResultCode.FAILED.value
            #     )
            #     or (isinstance(result, str) and result.upper() == "FAILED")
            # ):
            #     error_msg = f"GPM validation failed for GPM index {idx}."
            #     self._active_issues[f"gpm_{idx}"] = error_msg

        self.logger.info(
            "Active GPM-related issues after update: %s", self._active_issues
        )

    def _update_kvalue_issues(self) -> None:
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

    def _update_dishmanager_issues(self) -> None:
        """
        Update DishManager-related issues in active issues.

        This method checks the health state of the Dish Manager and updates
        the active issues dictionary if the health state is DEGRADED, FAILED,
        or UNKNOWN. It also logs the relevant error message.

        Returns:
            None
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
        self.logger.debug("Unexpected: No rule matched, defaulting to UNKNOWN")
        return HealthState.UNKNOWN

    def generate_health_info(self) -> Dict:
        """
        Generate health info dictionary from active issues.

        Returns:
            Dict containing health info
        """
        health_info: Dict = {"HealthSummary": []}
        health_info["HealthSummary"] = list(self._active_issues.values())
        return health_info
