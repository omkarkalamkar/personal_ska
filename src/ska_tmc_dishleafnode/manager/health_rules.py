"""
Rule engine definitions for Dish Leaf Node health state evaluation.
"""

from rule_engine import Rule
from ska_control_model import HealthState

HEALTH_RULES = {
    HealthState.OK: [
        Rule("kvalue_validation_result == 'OK'"),
    ],
    HealthState.FAILED: [
        Rule("kvalue_validation_result != 'OK'"),
    ],
}
