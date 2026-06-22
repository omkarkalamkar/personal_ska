"""Unit tests for SKB-1306 _sync_subsystem_availability."""

from unittest.mock import MagicMock

from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.dish_leaf_node import MidTmcLeafNodeDish


def _bind_publish(device: MagicMock) -> None:
    device._publish_subsystem_availability = (
        MidTmcLeafNodeDish._publish_subsystem_availability.__get__(
            device, MidTmcLeafNodeDish
        )
    )


def test_sync_does_not_overwrite_liveliness_true() -> None:
    """Init sync must not reset True set by the liveliness probe during retries."""
    device = MagicMock()
    device.DishAvailabilityCheckTimeout = 1
    device._is_subsystem_available = True
    device.component_manager.check_device_responsive.side_effect = (
        DeviceUnresponsive("not available")
    )
    _bind_publish(device)

    MidTmcLeafNodeDish._sync_subsystem_availability(device)

    assert device._is_subsystem_available is True


def test_sync_sets_true_when_dish_responsive() -> None:
    """Init sync publishes True when dish manager responds."""
    device = MagicMock()
    device.DishAvailabilityCheckTimeout = 1
    device._is_subsystem_available = False
    device.component_manager.check_device_responsive.return_value = None
    _bind_publish(device)

    MidTmcLeafNodeDish._sync_subsystem_availability(device)

    assert device._is_subsystem_available is True
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )
