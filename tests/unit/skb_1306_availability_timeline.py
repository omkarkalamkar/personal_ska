"""Timeline recorder for SKB-1306 isSubsystemAvailable diagnostics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TimelineEntry:
    """One traced step in the availability story."""

    elapsed_ms: float
    actor: str
    action: str
    value: bool | None = None


@dataclass
class AvailabilityTimeline:
    """Collect ordered availability events for tests and debug output."""

    _start: float = field(default_factory=time.monotonic)
    entries: list[TimelineEntry] = field(default_factory=list)

    def record(self, actor: str, action: str, value: bool | None = None) -> None:
        elapsed_ms = (time.monotonic() - self._start) * 1000
        self.entries.append(
            TimelineEntry(
                elapsed_ms=elapsed_ms,
                actor=actor,
                action=action,
                value=value,
            )
        )

    def values(self) -> list[bool | None]:
        return [entry.value for entry in self.entries]

    def actors_before_first_true_read(self) -> list[str]:
        before: list[str] = []
        for entry in self.entries:
            if entry.action.endswith("_read") and entry.value is True:
                break
            before.append(entry.actor)
        return before

    def format(self) -> str:
        lines = [
            "isSubsystemAvailable timeline (elapsed ms | actor | action | value)",
            "----------------------------------------------------------------",
        ]
        for entry in self.entries:
            value = "n/a" if entry.value is None else str(entry.value)
            lines.append(
                f"+{entry.elapsed_ms:8.1f}ms  {entry.actor:22s}  "
                f"{entry.action:32s}  {value}"
            )
        lines.append("")
        lines.append(self.summary())
        return "\n".join(lines)

    def summary(self) -> str:
        """One-line summary for sharing with the team."""
        first_true_read = next(
            (e for e in self.entries if e.action.endswith("_read") and e.value is True),
            None,
        )
        first_false_read = next(
            (e for e in self.entries if e.action.endswith("_read") and e.value is False),
            None,
        )
        first_event = next(
            (e for e in self.entries if e.action == "change_event"),
            None,
        )
        parts = []
        if first_false_read:
            parts.append(
                f"first False read +{first_false_read.elapsed_ms:.1f}ms "
                f"({first_false_read.action})"
            )
        if first_true_read:
            parts.append(
                f"first True read +{first_true_read.elapsed_ms:.1f}ms "
                f"({first_true_read.action})"
            )
        if first_event:
            parts.append(
                f"first change_event +{first_event.elapsed_ms:.1f}ms "
                f"value={first_event.value}"
            )
        if first_true_read and first_event:
            delta = first_event.elapsed_ms - first_true_read.elapsed_ms
            parts.append(f"event vs first True read delta={delta:+.1f}ms")
        return "Summary: " + ("; ".join(parts) if parts else "no reads/events recorded")

    def assert_order(self, *actors_in_order: str) -> None:
        """Assert actors appear in this order (not necessarily adjacent)."""
        indices = []
        search_from = 0
        for actor in actors_in_order:
            try:
                index = next(
                    i
                    for i, entry in enumerate(self.entries[search_from:], start=search_from)
                    if entry.actor == actor
                )
            except StopIteration as exc:
                raise AssertionError(
                    f"Expected actor '{actor}' in timeline.\n{self.format()}"
                ) from exc
            indices.append(index)
            search_from = index + 1
        if indices != sorted(indices):
            raise AssertionError(
                f"Actors not in order {actors_in_order}.\n{self.format()}"
            )
