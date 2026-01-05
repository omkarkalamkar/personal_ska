"""
Rule engine definitions for Dish Leaf Node health state evaluation.
"""

from rule_engine import Rule
from ska_control_model import HealthState

GOOD_STATES_SET = "{'STANDBY', 'CONFIGURING', 'OPERATE_FULL'}"

HEALTH_RULES = {
    HealthState.OK: [
        # Only OK if:
        # - A specific band is configured
        # - AND that band's capability is good
        Rule(
            "configured_band not in {'NONE', 'UNKNOWN'} and "
            f"band_capability_data.band_capabilities.get("
            f"configured_band.name, 'UNKNOWN') in {GOOD_STATES_SET}"
        ),
        Rule(
            "k_value_validation_result.result_code == 'OK' and "
            "$all([gpm != 'FAILED' for gpm in "
            "gpm_validation_result.result])"
        ),
    ],
    HealthState.DEGRADED: [
        Rule(
            "$any([gpm == 'FAILED' for gpm in "
            "gpm_validation_result.result])"
        ),
        # Configured band exists but is not in good state
        Rule(
            "configured_band not in {'NONE', 'UNKNOWN'} and "
            "band_capability_data.band_capabilities.get("
            f"configured_band.name, 'UNKNOWN') not in "
            f"{GOOD_STATES_SET}"
        ),
        # No band configured, but at least one band is good
        Rule(
            "configured_band in {'NONE', 'UNKNOWN'} and "
            "$any([state in "
            f"{GOOD_STATES_SET} for state in "
            "band_capability_data.band_capabilities.values()])"
        ),
    ],
    HealthState.FAILED: [
        Rule("k_value_validation_result.result_code != 'OK'"),
        # No usable band at all (only relevant when no band
        # configured)
        Rule(
            "configured_band in {'NONE', 'UNKNOWN'} and "
            "$all([state not in "
            f"{GOOD_STATES_SET} for state in "
            "band_capability_data.band_capabilities.values()])"
        ),
    ],
}
