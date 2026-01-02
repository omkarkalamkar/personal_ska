"""This module defines an enumerated type for StowStatus."""
import enum


class StowStatus(enum.IntEnum):
    """Python enumerated type for StowStatus."""

    DISH_NOT_IN_STOW = 0
    """A device reports this state when the dish is not in stow."""

    MANUAL_STOW_STARTED = 1
    """A device reports this state when the manual stowing is started."""

    MANUAL_STOW_COMPLETED = 2
    """
    The device reports this state when the manual stowing is completed.
    """

    MANUAL_STOW_FAILED = 3
    """
    The device reports this state when the manual stowing is failed.
    """

    WIND_STOW_STARTED = 4
    """
    The device reports this state when the stow is started automatically
    due to wind speed.
    There is a threshold set on device server.
    Whenever wind speed surpasses the threshold,
    the auto stow based on wind speed is triggered."""

    WIND_STOW_COMPLETED = 5
    """
    The device reports this state when the stow is started automatically
    due to wind speed is completed.
    """

    WIND_STOW_FAILED = 6
    """
    The device reports this state when the stow is started automatically
    due to wind speed is failed.
    """

    TEMP_STOW_STARTED = 7
    """
    The device reports this state when the stow is started automatically
    due to temperature.
    There is a threshold set on device server.
    Whenever temperature surpasses the threshold,
    the auto stow based on temperature is triggered.
    """

    TEMP_STOW_COMPLETED = 8
    """
    The device reports this state when the stow is started automatically
    due to temperature is completed.
    """
    TEMP_STOW_FAILED = 9
    """
    The device reports this state when the stow is started automatically
    due to temperature is failed.
    """
