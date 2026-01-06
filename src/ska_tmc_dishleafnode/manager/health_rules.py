"""
Rule engine definitions for Dish Leaf Node health state evaluation.
"""

from rule_engine import Rule
from ska_control_model import HealthState

GOOD_STATES_SET = (
    "{'STANDBY', 'CONFIGURING', 'OPERATE_FULL', 'OPERATE_DEGRADED', 'UNKNOWN'}"
)

HEALTH_RULES = {
    HealthState.OK: [
        # Only OK if:
        # - A band is requested
        # - AND that band's capability is good
        Rule(
            "k_value_validation_result.result_code == 'OK' and "
            "$all([gpm != 'FAILED' for gpm in "
            "gpm_validation_result.result]) and "
            "receiver_band not in {'NONE', 'UNKNOWN'} and "
            "band_capability_data.band_capabilities[receiver_band] in "
            f"{GOOD_STATES_SET}"
        ),
        # No band requested, but all bands band_capability_data are good
        Rule(
            "k_value_validation_result.result_code == 'OK' and "
            "$all([gpm != 'FAILED' for gpm in "
            "gpm_validation_result.result]) and "
            "receiver_band in {'NONE', 'UNKNOWN'} and "
            "$all(["
            f"state in {GOOD_STATES_SET} "
            "for state in band_capability_data.band_capability_values"
            "])"
        ),
    ],
    HealthState.DEGRADED: [
        Rule(
            "$any([gpm == 'FAILED' for gpm in "
            "gpm_validation_result.result])"
        ),
        # No band requested, but at least one band is good
        Rule(
            "k_value_validation_result.result_code == 'OK' and "
            f"receiver_band in {{'NONE', 'UNKNOWN'}} and "
            f"$any([state in {GOOD_STATES_SET} "
            f"for state in band_capability_data.band_capability_values])"
        ),
    ],
    HealthState.FAILED: [
        Rule("k_value_validation_result.result_code != 'OK'"),
        # No usable band at all (only relevant when no band
        # is requested)
        Rule(
            "receiver_band in {'NONE', 'UNKNOWN'} and "
            "$all([state not in "
            f"{GOOD_STATES_SET} for state in "
            "band_capability_data.band_capability_values])"
        ),
        # Configured band exists but is not in good state
        Rule(
            "receiver_band not in {'NONE', 'UNKNOWN'} and "
            "band_capability_data.band_capabilities[receiver_band] not in "
            f"{GOOD_STATES_SET}"
        ),
    ],
}
