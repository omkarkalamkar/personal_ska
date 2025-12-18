"""
Dataclass representing inputs used by the rule engine to evaluate health state.
"""

from dataclasses import dataclass

from ska_tango_base.commands import ResultCode


@dataclass
class DishHealthData:
    """
    Context object passed to health rule engine.

    Extend this dataclass when new health inputs
    (PTT, GPM, etc.) are added.
    """

    kvalue_result: ResultCode
