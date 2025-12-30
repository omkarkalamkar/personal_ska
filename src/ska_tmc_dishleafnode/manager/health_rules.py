"""
Rule engine definitions for Dish Leaf Node health state evaluation.
"""

from rule_engine import Rule
from ska_control_model import HealthState

HEALTH_RULES = {
    HealthState.OK: [
        Rule("kvalue_validation_result == 'OK'"),
        Rule("$all([gpm != 'FAILED' for gpm in gpm_validation_result ])"),
    ],
    HealthState.FAILED: [
        Rule("kvalue_validation_result != 'OK'"),
    ],
    HealthState.DEGRADED: [
        Rule("$any([gpm == 'FAILED' for gpm in gpm_validation_result ])"),
    ],
}
