"""SKB-1306 failure-mode tests: isSubsystemAvailable on signal-based 0.45.0.

Root fix: drop Signal(initial_value=False) and set True at init when responsive.
Signal assignment goes through the bus; attribute_from_signal updates reads/events.

Run:

    poetry run pytest tests/unit/test_skb_1306_sn_failure_modes.py -v
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_tango_base.software_bus import Signal, SignalBusMixin, attribute_from_signal
from tango import AttrWriteType
from tango.server import Device, command
from tango.test_context import DeviceTestContext

from ska_tmc_dishleafnode.dish_leaf_node import MidTmcLeafNodeDish

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")


def _subscribe_change_events(device_proxy: tango.DeviceProxy) -> tuple[int, list[bool]]:
    received: list[bool] = []

    def _callback(event: tango.EventData) -> None:
        if not event.err:
            received.append(event.attr_value.value)

    event_id = device_proxy.subscribe_event(
        "isSubsystemAvailable",
        tango.EventType.CHANGE_EVENT,
        _callback,
    )
    return event_id, received


def _wait_for_event_value(received: list[bool], expected: bool, timeout: float = 10) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if expected in received:
            return True
        time.sleep(0.1)
    return False


class _SignalOnlyLeafNode(SignalBusMixin, Device):
    """0.45.0-style callback: assign signal only (no explicit event push)."""

    _is_subsystem_available: Signal[bool] = Signal[bool](
        stored=True, initial_value=False
    )

    isSubsystemAvailable = attribute_from_signal(
        _is_subsystem_available,
        access=AttrWriteType.READ,
        dtype=bool,
        description="Boolean Flag for sub system available",
    )

    def init_device(self) -> None:
        super().init_device()

    @command
    def SimulateLivelinessCallback(self, available: bool) -> None:
        self._is_subsystem_available = available


class _FixedSignalLeafNode(SignalBusMixin, Device):
    """SKB-1306 fix: no initial_value=False on the signal."""

    _is_subsystem_available: Signal[bool] = Signal[bool](stored=True)

    isSubsystemAvailable = attribute_from_signal(
        _is_subsystem_available,
        access=AttrWriteType.READ,
        dtype=bool,
    )

    def init_device(self) -> None:
        super().init_device()

    @command
    def SimulateLivelinessCallback(self, available: bool) -> None:
        self._is_subsystem_available = available


def test_signal_initial_value_false_starts_false() -> None:
    device = MagicMock()
    device._is_subsystem_available = False
    assert device._is_subsystem_available is False


def test_assign_resources_style_read_before_liveliness_is_false() -> None:
    with DeviceTestContext(_SignalOnlyLeafNode, process=True) as device_proxy:
        assert device_proxy.isSubsystemAvailable is False
        subarray_read = tango.DeviceProxy(device_proxy.dev_name()).isSubsystemAvailable
        assert subarray_read is False
        device_proxy.SimulateLivelinessCallback(True)
        time.sleep(0.2)
        assert device_proxy.isSubsystemAvailable is True


def test_fixed_signal_no_startup_false_before_liveliness() -> None:
    with DeviceTestContext(_FixedSignalLeafNode, process=True) as device_proxy:
        attr = device_proxy.read_attribute("isSubsystemAvailable")
        assert attr.quality != tango.AttrQuality.ATTR_VALID or attr.value is not True


def test_repair_restores_true_when_cache_stale_and_dish_responsive() -> None:
    device = MagicMock()
    device._subsystem_available_confirmed = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": False}
    device.component_manager.check_device_responsive.return_value = None
    device._sync_subsystem_availability_read_cache = (
        MidTmcLeafNodeDish._sync_subsystem_availability_read_cache.__get__(
            device, MidTmcLeafNodeDish
        )
    )
    device._repair_subsystem_availability_if_needed = (
        MidTmcLeafNodeDish._repair_subsystem_availability_if_needed.__get__(
            device, MidTmcLeafNodeDish
        )
    )
    device._repair_subsystem_availability_if_needed()
    assert device._is_subsystem_available is True
    assert device._SignalBusMixin__attr_values["isSubsystemAvailable"] is True
    device.push_change_archive_events.assert_called_with(
        "isSubsystemAvailable", True
    )


def test_repair_skips_when_not_confirmed() -> None:
    device = MagicMock()
    device._subsystem_available_confirmed = False
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": False}
    device._repair_subsystem_availability_if_needed = (
        MidTmcLeafNodeDish._repair_subsystem_availability_if_needed.__get__(
            device, MidTmcLeafNodeDish
        )
    )
    device._repair_subsystem_availability_if_needed()
    device.component_manager.check_device_responsive.assert_not_called()


def test_repair_skips_when_cache_already_true() -> None:
    device = MagicMock()
    device._subsystem_available_confirmed = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": True}
    device._repair_subsystem_availability_if_needed = (
        MidTmcLeafNodeDish._repair_subsystem_availability_if_needed.__get__(
            device, MidTmcLeafNodeDish
        )
    )
    device._repair_subsystem_availability_if_needed()
    device.component_manager.check_device_responsive.assert_not_called()


def test_notify_emission_blocks_stale_false_when_confirmed() -> None:
    device = MagicMock()
    device._subsystem_available_confirmed = True
    device._SignalBusMixin__attr_values = {}
    device.component_manager.check_device_responsive.return_value = None
    device._sync_subsystem_availability_read_cache = (
        MidTmcLeafNodeDish._sync_subsystem_availability_read_cache.__get__(
            device, MidTmcLeafNodeDish
        )
    )
    with patch.object(SignalBusMixin, "notify_emission") as super_notify:
        MidTmcLeafNodeDish.notify_emission(
            device, "._is_subsystem_available", False
        )
    super_notify.assert_not_called()
    device.push_change_archive_events.assert_called_with(
        "isSubsystemAvailable", True
    )


def test_dish_callback_assigns_signal() -> None:
    device = MagicMock()
    device._is_subsystem_available = False
    device.update_availablity_callback = (
        MidTmcLeafNodeDish.update_availablity_callback.__get__(
            device, MidTmcLeafNodeDish
        )
    )
    device.update_availablity_callback(True)
    assert device._is_subsystem_available is True


def test_subscriber_gets_true_after_signal_liveliness_update() -> None:
    with DeviceTestContext(_FixedSignalLeafNode, process=True) as device_proxy:
        event_id, received = _subscribe_change_events(device_proxy)
        try:
            time.sleep(0.5)
            device_proxy.SimulateLivelinessCallback(True)
            assert _wait_for_event_value(received, True)
            assert device_proxy.isSubsystemAvailable is True
        finally:
            device_proxy.unsubscribe_event(event_id)
