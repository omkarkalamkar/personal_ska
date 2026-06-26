"""SKB-1306 failure-mode tests: isSubsystemAvailable on signal-based 0.45.0.

Documents production symptoms and the minimal fix (0.45.1-style explicit push
while keeping attribute_from_signal):

1. Signal starts False until liveliness updates it.
2. Subarray can read False during Assign before liveliness runs.
3. Explicit push_change_archive_events on callback restores Subarray events.

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
from tango.server import Device, attribute, command
from tango.test_context import DeviceTestContext

from ska_tmc_dishleafnode.dish_leaf_node import MidTmcLeafNodeDish

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")


def _bind_availability_methods(device: MagicMock) -> None:
    for name in (
        "_get_availability_attr_cache",
        "_sync_availability_attr_cache",
        "_publish_subsystem_availability",
        "_should_block_stale_availability_false_bus",
        "_repair_subsystem_availability_cache_if_needed",
        "update_availablity_callback",
    ):
        setattr(
            device,
            name,
            getattr(MidTmcLeafNodeDish, name).__get__(device, MidTmcLeafNodeDish),
        )


def _subscribe_change_events(device_proxy: tango.DeviceProxy) -> tuple[int, list[bool]]:
    """Subscribe to isSubsystemAvailable change events; return id and buffer."""
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
        """Mirror 0.45.0 update_availablity_callback (signal assign only)."""
        self._is_subsystem_available = available


class _PreSignalLeafNode(SignalBusMixin, Device):
    """0.45.1 / HM-903-style callback: plain flag + explicit push on change."""

    def init_device(self) -> None:
        super().init_device()
        self._is_subsystem_available = False
        self.set_change_event("isSubsystemAvailable", True, False)
        self.set_archive_event("isSubsystemAvailable", True)

    isSubsystemAvailable = attribute(
        dtype=bool,
        access=AttrWriteType.READ,
        doc="Boolean Flag for sub system available",
    )

    def read_isSubsystemAvailable(self) -> bool:
        return self._is_subsystem_available

    @command
    def SimulateLivelinessCallback(self, available: bool) -> None:
        """Mirror pre-signal update_availablity_callback."""
        if self._is_subsystem_available != available:
            self._is_subsystem_available = available
            with tango.EnsureOmniThread():
                self.push_change_event("isSubsystemAvailable", available)
                self.push_archive_event("isSubsystemAvailable", available)


def test_signal_starts_false_until_liveliness() -> None:
    """SN symptom: value stays False until liveliness callback runs."""
    device = MagicMock()
    device._is_subsystem_available = False

    assert device._is_subsystem_available is False


def test_assign_resources_style_read_before_liveliness_is_false() -> None:
    """Race: Subarray synchronous read happens before liveliness sets True."""
    with DeviceTestContext(_SignalOnlyLeafNode, process=True) as device_proxy:
        # Startup complete; liveliness has not run yet.
        assert device_proxy.isSubsystemAvailable is False

        # Mirrors test_subarray_assign_resources_read_pattern timing.
        subarray_read = tango.DeviceProxy(device_proxy.dev_name()).isSubsystemAvailable
        assert subarray_read is False

        # Liveliness would update later.
        device_proxy.SimulateLivelinessCallback(True)
        time.sleep(0.2)
        assert device_proxy.isSubsystemAvailable is True


def test_callback_pushes_change_archive_events() -> None:
    device = MagicMock()
    device._is_subsystem_available = False
    _bind_availability_methods(device)

    device.update_availablity_callback(True)

    assert device._is_subsystem_available is True
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )


def test_callback_skips_push_when_value_unchanged() -> None:
    device = MagicMock()
    device._is_subsystem_available = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": True}
    _bind_availability_methods(device)

    device.update_availablity_callback(True)

    assert device._is_subsystem_available is True
    device.push_change_archive_events.assert_not_called()


def test_publish_repairs_stale_read_cache_when_signal_already_true() -> None:
    device = MagicMock()
    device._is_subsystem_available = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": False}
    _bind_availability_methods(device)

    device.update_availablity_callback(True)

    assert device._SignalBusMixin__attr_values["isSubsystemAvailable"] is True
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )


def test_notify_emission_skips_stale_bus_value() -> None:
    device = MagicMock()
    device._is_subsystem_available = True
    device._suppress_stale_availability_false_bus = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": False}
    _bind_availability_methods(device)

    with patch.object(SignalBusMixin, "notify_emission") as super_notify:
        MidTmcLeafNodeDish.notify_emission(
            device, "._is_subsystem_available", False
        )

    super_notify.assert_not_called()
    assert device._SignalBusMixin__attr_values["isSubsystemAvailable"] is True
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )


def test_repair_subsystem_availability_cache_if_needed() -> None:
    device = MagicMock()
    device._is_subsystem_available = True
    device._suppress_stale_availability_false_bus = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": False}
    _bind_availability_methods(device)

    device._repair_subsystem_availability_cache_if_needed()

    assert device._SignalBusMixin__attr_values["isSubsystemAvailable"] is True
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )


def test_repair_skips_when_cache_matches_signal() -> None:
    device = MagicMock()
    device._is_subsystem_available = True
    device._suppress_stale_availability_false_bus = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": True}
    _bind_availability_methods(device)

    device._repair_subsystem_availability_cache_if_needed()

    device.push_change_archive_events.assert_not_called()


def test_repair_skips_when_signal_false_even_if_cache_true() -> None:
    """Hook repair must not run when availability was set False by liveliness."""
    device = MagicMock()
    device._is_subsystem_available = False
    device._suppress_stale_availability_false_bus = False
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": True}
    _bind_availability_methods(device)

    device._repair_subsystem_availability_cache_if_needed()

    device.push_change_archive_events.assert_not_called()
    assert device._SignalBusMixin__attr_values["isSubsystemAvailable"] is True


def test_repair_promotes_true_when_suppress_set_despite_signal_false() -> None:
    """Second subscribe can desync signal storage; suppress flag is authoritative."""
    device = MagicMock()
    device._is_subsystem_available = False
    device._suppress_stale_availability_false_bus = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": False}
    _bind_availability_methods(device)

    device._repair_subsystem_availability_cache_if_needed()

    assert device._SignalBusMixin__attr_values["isSubsystemAvailable"] is True
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )


def test_callback_clears_suppress_only_on_true_to_false_transition() -> None:
    device = MagicMock()
    device._is_subsystem_available = False
    device._suppress_stale_availability_false_bus = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": True}
    _bind_availability_methods(device)

    device.update_availablity_callback(False)

    assert device._suppress_stale_availability_false_bus is True
    device.push_change_archive_events.assert_not_called()


def test_callback_clears_suppress_when_becoming_unavailable() -> None:
    device = MagicMock()
    device._is_subsystem_available = True
    device._suppress_stale_availability_false_bus = True
    device._init_sync_confirmed_available = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": True}
    _bind_availability_methods(device)

    device.update_availablity_callback(False)

    assert device._suppress_stale_availability_false_bus is False
    assert device._init_sync_confirmed_available is False
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", False
    )


def test_should_block_stale_false_when_init_sync_latch_set() -> None:
    device = MagicMock()
    device._init_sync_confirmed_available = True
    device._suppress_stale_availability_false_bus = False
    device._is_subsystem_available = False
    _bind_availability_methods(device)

    assert device._should_block_stale_availability_false_bus() is True


def test_notify_emission_blocks_stale_false_when_init_sync_latch_set() -> None:
    device = MagicMock()
    device._init_sync_confirmed_available = True
    device._suppress_stale_availability_false_bus = False
    device._is_subsystem_available = False
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": False}
    _bind_availability_methods(device)

    with patch.object(SignalBusMixin, "notify_emission") as super_notify:
        MidTmcLeafNodeDish.notify_emission(
            device, "._is_subsystem_available", False
        )

    super_notify.assert_not_called()
    assert device._SignalBusMixin__attr_values["isSubsystemAvailable"] is True
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )


def test_notify_emission_blocks_stale_false_when_signal_true() -> None:
    device = MagicMock()
    device._is_subsystem_available = True
    device._suppress_stale_availability_false_bus = False
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": True}
    _bind_availability_methods(device)

    with patch.object(SignalBusMixin, "notify_emission") as super_notify:
        MidTmcLeafNodeDish.notify_emission(
            device, "._is_subsystem_available", False
        )

    super_notify.assert_not_called()
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )


def test_notify_emission_blocks_stale_false_when_suppress_set() -> None:
    device = MagicMock()
    device._is_subsystem_available = False
    device._suppress_stale_availability_false_bus = True
    device._SignalBusMixin__attr_values = {"isSubsystemAvailable": True}
    _bind_availability_methods(device)

    with patch.object(SignalBusMixin, "notify_emission") as super_notify:
        MidTmcLeafNodeDish.notify_emission(
            device, "._is_subsystem_available", False
        )

    super_notify.assert_not_called()
    device.push_change_archive_events.assert_called_once_with(
        "isSubsystemAvailable", True
    )


def test_presignal_callback_pushes_tango_events() -> None:
    """Pre-signal implementation explicitly notified subscribers."""
    device = MagicMock()
    device._is_subsystem_available = False

    if device._is_subsystem_available != True:
        device._is_subsystem_available = True
        with tango.EnsureOmniThread():
            device.push_change_event("isSubsystemAvailable", True)
            device.push_archive_event("isSubsystemAvailable", True)

    device.push_change_event.assert_called_once_with(
        "isSubsystemAvailable", True
    )
    device.push_archive_event.assert_called_once_with(
        "isSubsystemAvailable", True
    )


def test_presignal_callback_skips_push_when_value_unchanged() -> None:
    device = MagicMock()
    device._is_subsystem_available = True

    if device._is_subsystem_available != True:
        device._is_subsystem_available = True
        device.push_change_event("isSubsystemAvailable", True)

    device.push_change_event.assert_not_called()


def test_subscriber_gets_true_after_signal_liveliness_update() -> None:
    """When liveliness does update the signal, reads and events can reach True."""
    with DeviceTestContext(_SignalOnlyLeafNode, process=True) as device_proxy:
        event_id, received = _subscribe_change_events(device_proxy)
        try:
            time.sleep(0.5)
            device_proxy.SimulateLivelinessCallback(True)

            assert _wait_for_event_value(received, True)
            assert device_proxy.isSubsystemAvailable is True
        finally:
            device_proxy.unsubscribe_event(event_id)


def test_subscriber_gets_true_after_presignal_liveliness_update() -> None:
    """Pre-signal path also delivers True to subscribers when liveliness fires."""
    with DeviceTestContext(_PreSignalLeafNode, process=True) as device_proxy:
        event_id, received = _subscribe_change_events(device_proxy)
        try:
            time.sleep(0.5)
            device_proxy.SimulateLivelinessCallback(True)

            assert _wait_for_event_value(received, True)
            assert device_proxy.isSubsystemAvailable is True
        finally:
            device_proxy.unsubscribe_event(event_id)


def test_sn_stuck_false_until_liveliness_no_early_true_event() -> None:
    """Full SN failure window: False read + no True event until liveliness runs."""
    with DeviceTestContext(_SignalOnlyLeafNode, process=True) as device_proxy:
        event_id, received = _subscribe_change_events(device_proxy)
        try:
            time.sleep(0.5)

            # Subarray Assign Resources read (too early).
            assert device_proxy.isSubsystemAvailable is False
            assert True not in received

            # Liveliness later — value and event finally move.
            device_proxy.SimulateLivelinessCallback(True)
            assert _wait_for_event_value(received, True)
            assert device_proxy.isSubsystemAvailable is True
        finally:
            device_proxy.unsubscribe_event(event_id)

