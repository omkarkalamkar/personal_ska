"""
Rule engine definitions for Dish Leaf Node health state evaluation.
"""

from rule_engine import Rule
from ska_control_model import HealthState

GOOD_CAPABILITY_STATES = {
    "STANDBY",
    "CONFIGURING",
    "OPERATE_FULL",
    "OPERATE_DEGRADED",
    "UNKNOWN",
}

HEALTH_RULES = {
    HealthState.OK: [
        # Case 1: Specific band configured and fully capable
        Rule(
            "k_value_validation_result.result_code == 'OK' and "
            "$all([gpm != 'FAILED' for gpm in gpm_validation_result.result]) "
            "and receiver_band not in {'NONE', 'UNKNOWN'} and "
            "band_capability_data.band_capabilities[receiver_band] "
            f"in {GOOD_CAPABILITY_STATES}"
        ),
        # Case 2: No band configured, all bands good
        Rule(
            "k_value_validation_result.result_code == 'OK' and "
            "$all([gpm != 'FAILED' for gpm in gpm_validation_result.result]) "
            "and receiver_band in {'NONE', 'UNKNOWN'} and "
            "$all([state in "
            f"{GOOD_CAPABILITY_STATES} for state in "
            "band_capability_data.band_capability_values])"
        ),
    ],
    HealthState.DEGRADED: [
        # Any GPM failed
        Rule(
            "$any([gpm == 'FAILED' for gpm in gpm_validation_result.result])"
        ),
        # Configured band not fully capable (KValue and GPM are OK)
        Rule(
            "k_value_validation_result.result_code == 'OK' and "
            "$all([gpm != 'FAILED' for gpm in gpm_validation_result.result]) "
            "and receiver_band not in {'NONE', 'UNKNOWN'} and "
            "band_capability_data.band_capabilities[receiver_band] "
            f"not in {GOOD_CAPABILITY_STATES}"
        ),
        # No band configured, but some bands are bad (partial capability)
        Rule(
            "k_value_validation_result.result_code == 'OK' and "
            "$all([gpm != 'FAILED' for gpm in gpm_validation_result.result]) "
            "and receiver_band in {'NONE', 'UNKNOWN'} and "
            "$any([state in "
            f"{GOOD_CAPABILITY_STATES} for state in "
            "band_capability_data.band_capability_values]) and "
            "$any([state not in "
            f"{GOOD_CAPABILITY_STATES} for state in "
            "band_capability_data.band_capability_values])"
        ),
    ],
    HealthState.FAILED: [
        # KValue validation failed (critical)
        Rule("k_value_validation_result.result_code != 'OK'"),
        # No band configured and ALL bands unavailable
        Rule(
            "receiver_band in {'NONE', 'UNKNOWN'} and "
            "$all([state not in "
            f"{GOOD_CAPABILITY_STATES} for state in "
            "band_capability_data.band_capability_values])"
        ),
    ],
    HealthState.UNKNOWN: [
        Rule("True"),
    ],
}
