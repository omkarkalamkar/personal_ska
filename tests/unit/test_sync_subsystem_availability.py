"""Unit tests for SKB-1306 init sync in init_device."""

from unittest.mock import MagicMock

from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.dish_leaf_node import MidTmcLeafNodeDish


def _run_init_sync(device: MagicMock) -> None:
    device.update_availablity_callback = (
        MidTmcLeafNodeDish.update_availablity_callback.__get__(
            device, MidTmcLeafNodeDish
        )
    )
    try:
        device.component_manager.check_device_responsive()
        device.update_availablity_callback(True)
    except DeviceUnresponsive:
        pass


def test_sync_does_not_overwrite_liveliness_true() -> None:
    device = MagicMock()
    device._is_subsystem_available = True
    device.component_manager.check_device_responsive.side_effect = (
        DeviceUnresponsive("not available")
    )
    _run_init_sync(device)
    assert device._is_subsystem_available is True


def test_sync_sets_true_when_dish_responsive() -> None:
    device = MagicMock()
    device._is_subsystem_available = False
    device.component_manager.check_device_responsive.return_value = None
    _run_init_sync(device)
    assert device._is_subsystem_available is True
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )
