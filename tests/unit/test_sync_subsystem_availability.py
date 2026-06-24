"""Unit tests for SKB-1306 init sync loop in init_device."""

from unittest.mock import MagicMock

from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.dish_leaf_node import MidTmcLeafNodeDish


def _bind_availability_methods(device: MagicMock) -> None:
    for name in (
        "_get_availability_attr_cache",
        "_sync_availability_attr_cache",
        "_publish_subsystem_availability",
        "_log_availability",
        "update_availablity_callback",
    ):
        setattr(
            device,
            name,
            getattr(MidTmcLeafNodeDish, name).__get__(device, MidTmcLeafNodeDish),
        )
    device._availability_init_mono = 0.0
    device._log_availability = lambda event, **fields: None


def _run_init_sync(device: MagicMock) -> None:
    _bind_availability_methods(device)
    timeout = int(device.DishAvailabilityCheckTimeout)
    for attempt in range(timeout):
        try:
            device.component_manager.check_device_responsive()
            device.update_availablity_callback(True)
            break
        except DeviceUnresponsive:
            if attempt < timeout - 1:
                pass


def test_sync_does_not_overwrite_liveliness_true() -> None:
    device = MagicMock()
    device.DishAvailabilityCheckTimeout = 1
    device._is_subsystem_available = True
    device.component_manager.check_device_responsive.side_effect = (
        DeviceUnresponsive("not available")
    )
    _run_init_sync(device)
    assert device._is_subsystem_available is True


def test_sync_sets_true_when_dish_responsive() -> None:
    device = MagicMock()
    device.DishAvailabilityCheckTimeout = 1
    device._is_subsystem_available = False
    device.component_manager.check_device_responsive.return_value = None
    _run_init_sync(device)
    assert device._is_subsystem_available is True
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )


def test_sync_retries_until_dish_responsive() -> None:
    device = MagicMock()
    device.DishAvailabilityCheckTimeout = 3
    device._is_subsystem_available = False
    device.component_manager.check_device_responsive.side_effect = [
        DeviceUnresponsive("not yet"),
        DeviceUnresponsive("not yet"),
        None,
    ]
    _run_init_sync(device)
    assert device._is_subsystem_available is True
    assert device.component_manager.check_device_responsive.call_count == 3
