"""
Rule engine definitions for Dish Leaf Node health state evaluation.
"""

from rule_engine import Rule
from ska_control_model import HealthState

# from ska_tango_base.commands import ResultCode

HEALTH_RULES = {
    HealthState.OK: [
        Rule("kvalue_result == 'OK'"),
    ],
    HealthState.DEGRADED: [
        Rule("kvalue_result != 'OK'"),
    ],
}
