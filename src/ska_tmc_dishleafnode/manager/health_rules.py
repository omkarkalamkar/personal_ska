"""
Rule engine definitions for Dish Leaf Node health state evaluation.
"""

from rule_engine import Rule
from ska_control_model import HealthState

HEALTH_RULES = {
    HealthState.FAILED: [
        Rule('ptt_status == "ERROR_PRESENT"'),
    ],
    HealthState.DEGRADED: [
        Rule('kvalue_status == "MISMATCH"'),
        Rule('kvalue_status == "UNKNOWN"'),
    ],
    HealthState.OK: [
        Rule('ptt_status == "NO_ERROR" and ' 'kvalue_status == "OK"'),
    ],
}
