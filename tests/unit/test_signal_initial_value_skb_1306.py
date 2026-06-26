"""SKB-1306 root cause: Signal(initial_value=False) auto-emits on bus connect.

ska-tango-base SharingObserver.shared_bus setter emits initial_value for every
Signal. That queues False on the async bus and seeds __attr_values before
liveliness runs. Removing initial_value avoids the startup poison emission.
"""

from __future__ import annotations

import time

import pytest
import tango
from ska_tango_base.software_bus import Signal, SignalBusMixin, attribute_from_signal
from tango import AttrWriteType
from tango.server import Device, command
from tango.test_context import DeviceTestContext

pytestmark = pytest.mark.xdist_group(name="skb1306_is_subsystem_available")


def _read_bool(proxy: tango.DeviceProxy) -> bool | None:
    attr = proxy.read_attribute("isSubsystemAvailable")
    if attr.quality == tango.AttrQuality.ATTR_VALID:
        return attr.value
    return None


class _ProbeWithInitialFalse(SignalBusMixin, Device):
    _is_subsystem_available: Signal[bool] = Signal[bool](
        stored=True, initial_value=False
    )
    isSubsystemAvailable = attribute_from_signal(
        _is_subsystem_available, access=AttrWriteType.READ, dtype=bool
    )

    def init_device(self) -> None:
        super().init_device()

    @command
    def SetTrue(self) -> None:
        self._is_subsystem_available = True


class _ProbeWithoutInitial(SignalBusMixin, Device):
    _is_subsystem_available: Signal[bool] = Signal[bool](stored=True)
    isSubsystemAvailable = attribute_from_signal(
        _is_subsystem_available, access=AttrWriteType.READ, dtype=bool
    )

    def init_device(self) -> None:
        super().init_device()

    @command
    def SetTrue(self) -> None:
        self._is_subsystem_available = True


def test_initial_value_false_makes_startup_read_false() -> None:
    with DeviceTestContext(_ProbeWithInitialFalse, process=True) as proxy:
        time.sleep(0.3)
        assert _read_bool(proxy) is False


def test_no_initial_value_startup_read_invalid_until_set() -> None:
    with DeviceTestContext(_ProbeWithoutInitial, process=True) as proxy:
        time.sleep(0.3)
        assert _read_bool(proxy) is None


def test_without_initial_value_subscribe_stays_true() -> None:
    with DeviceTestContext(_ProbeWithoutInitial, process=True) as proxy:
        proxy.SetTrue()
        time.sleep(0.3)
        fresh = tango.DeviceProxy(proxy.dev_name())
        event_id = fresh.subscribe_event(
            "isSubsystemAvailable", tango.EventType.CHANGE_EVENT, lambda _: None
        )
        try:
            time.sleep(0.5)
            assert _read_bool(fresh) is True
        finally:
            fresh.unsubscribe_event(event_id)
