"""
Rule engine definitions for Dish Leaf Node health state evaluation.
"""

from rule_engine import Rule
from ska_control_model import HealthState

HEALTH_RULES = {
    HealthState.OK: [
        Rule(
            "k_value_validation_result.result_code == 'OK' and "
            "$all([gpm != 'FAILED' for gpm in gpm_validation_result.result])"
        ),
    ],
    HealthState.DEGRADED: [
        Rule(
            "$any([gpm == 'FAILED' for gpm in gpm_validation_result.result])"
        ),
    ],
    HealthState.FAILED: [
        Rule("k_value_validation_result.result_code != 'OK'"),
    ],
}
