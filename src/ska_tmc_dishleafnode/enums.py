"""Enumeration module for Dish Leaf Node"""
from enum import Enum


class CORRECTION_KEY(Enum):
    """This class provides enumeration values which
    is checked against correction key provided in
    Dish leaf node Configure JSON.
    """

    RESET = "RESET"
    UPDATE = "UPDATE"
    MAINTAIN = "MAINTAIN"
    NOT_SET = ""
