"""This module defines an enumerated type for StowStatus."""
import enum


class StowStatus(enum.IntEnum):
    """Python enumerated type for StowStatus."""

    DISH_NOT_IN_STOW = 0
    """A device reports this state when the dish is not in stow."""

    STOW_STARTED = 1
    """A device reports this state when the stow operation is started."""

    STOW_COMPLETED = 2
    """
    The device reports this state when the stow operation is completed.
    """

    STOW_FAILED = 3
    """
    The device reports this state when the stow operation is failed.
    """
