"""Unit tests for SKB-1306 init sync."""

from unittest.mock import MagicMock

from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.dish_leaf_node import MidTmcLeafNodeDish


def _bind_set_availability(device: MagicMock) -> None:
    device._set_subsystem_availability = (
        MidTmcLeafNodeDish._set_subsystem_availability.__get__(
            device, MidTmcLeafNodeDish
        )
    )


def test_sync_does_not_overwrite_liveliness_true() -> None:
    device = MagicMock()
    device.DishAvailabilityCheckTimeout = 1
    device._is_subsystem_available = True
    device.component_manager.check_device_responsive.side_effect = (
        DeviceUnresponsive("not available")
    )
    _bind_set_availability(device)

    MidTmcLeafNodeDish._sync_subsystem_availability(device)

    assert device._is_subsystem_available is True


def test_sync_sets_true_when_dish_responsive() -> None:
    device = MagicMock()
    device.DishAvailabilityCheckTimeout = 1
    device._is_subsystem_available = False
    device.component_manager.check_device_responsive.return_value = None
    _bind_set_availability(device)

    MidTmcLeafNodeDish._sync_subsystem_availability(device)

    assert device._is_subsystem_available is True
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )
