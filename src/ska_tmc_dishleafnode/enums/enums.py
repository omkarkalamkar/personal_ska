"""Enumeration module for Dish Leaf Node"""
from enum import Enum, IntEnum


class CORRECTION_KEY(Enum):
    """This class provides enumeration values which
    is checked against correction key provided in
    Dish leaf node Configure JSON.
    """

    RESET = "RESET"
    UPDATE = "UPDATE"
    MAINTAIN = "MAINTAIN"
    NOT_SET = ""


class CommandResult(Enum):
    """
    Pointing state of the dish.
    """

    NONE = "NONE"
    NOT_ACHIEVED = "NOT_ACHIEVED"
    ACHIEVED = "ACHIEVED"
    ABORTED = "ABORTED"


class CapabilityStates(IntEnum):
    """
    This is an enumerator class that contains CapabilityStates values.
    """

    UNAVAILABLE = 0
    STANDBY = 1
    CONFIGURING = 2
    OPERATE_DEGRADED = 3
    OPERATE_FULL = 4
    UNKNOWN = 5
