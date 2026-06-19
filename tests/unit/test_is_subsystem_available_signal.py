"""Tests for isSubsystemAvailable using attribute_from_signal (SKB-1306)."""

import threading
import time

import tango
from ska_tango_base.software_bus import Signal, SignalBusMixin, attribute_from_signal
from tango import AttrWriteType
from tango.server import Device, command
from tango.test_context import DeviceTestContext


class _AvailabilityLeafNode(SignalBusMixin, Device):
    """Minimal device reproducing the SKB-1306 attribute_from_signal pattern."""

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
    def SetAvailability(self, available: bool) -> None:
        """Simulate component manager availability callback."""
        self._is_subsystem_available = available

    @command
    def SetAvailabilityFromThread(self, available: bool) -> None:
        """Simulate liveliness probe updating availability from a thread."""
        done = threading.Event()

        def _set() -> None:
            with tango.EnsureOmniThread():
                self._is_subsystem_available = available
            done.set()

        threading.Thread(target=_set, daemon=True).start()
        done.wait(timeout=5)


def test_attribute_from_signal_read_after_availability_becomes_true() -> None:
    """Subarray reads isSubsystemAvailable after dish becomes available."""
    with DeviceTestContext(_AvailabilityLeafNode, process=True) as device_proxy:
        assert device_proxy.isSubsystemAvailable is False

        device_proxy.SetAvailability(True)
        time.sleep(0.2)

        assert device_proxy.isSubsystemAvailable is True
        attr = device_proxy.read_attribute("isSubsystemAvailable")
        assert attr.quality == tango.AttrQuality.ATTR_VALID
        assert attr.value is True


def test_attribute_from_signal_change_event_reaches_subscriber() -> None:
    """Subarray event subscription must receive True after availability update."""
    with DeviceTestContext(_AvailabilityLeafNode, process=True) as device_proxy:
        received: list[bool] = []

        def _callback(event: tango.EventData) -> None:
            if not event.err:
                received.append(event.attr_value.value)

        event_id = device_proxy.subscribe_event(
            "isSubsystemAvailable",
            tango.EventType.CHANGE_EVENT,
            _callback,
        )
        try:
            # Allow the event subscription to register before changing the attribute.
            time.sleep(0.5)
            device_proxy.SetAvailability(True)
            deadline = time.time() + 10
            while time.time() < deadline and True not in received:
                time.sleep(0.1)
            assert True in received, f"Expected change event True, got {received}"
        finally:
            device_proxy.unsubscribe_event(event_id)


def test_attribute_from_signal_update_from_background_thread() -> None:
    """Availability update from liveliness probe thread must be readable."""
    with DeviceTestContext(_AvailabilityLeafNode, process=True) as device_proxy:
        device_proxy.SetAvailabilityFromThread(True)
        deadline = time.time() + 10
        while time.time() < deadline:
            if device_proxy.isSubsystemAvailable is True:
                break
            time.sleep(0.1)
        assert device_proxy.isSubsystemAvailable is True
