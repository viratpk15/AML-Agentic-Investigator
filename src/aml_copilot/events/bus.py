"""Per-investigation event bus and manager for asynchronous SSE streaming."""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Set

from aml_copilot.events.models import EventType, InvestigationEvent
from aml_copilot.logger import get_logger
from aml_copilot.reporting.models import InvestigationReport

logger = get_logger(__name__)


class InvestigationEventBus:
    """Isolated per-investigation event bus with history retention and real-time subscription."""

    def __init__(self, investigation_id: str):
        self.investigation_id = investigation_id
        self.status: str = "QUEUED"  # QUEUED, RUNNING, COMPLETED, FAILED
        self._events: List[InvestigationEvent] = []
        self._subscribers: Set[asyncio.Queue[Optional[InvestigationEvent]]] = set()
        self.report: Optional[InvestigationReport] = None
        self.markdown: Optional[str] = None
        self.error: Optional[str] = None
        self.start_time: float = time.time()
        self.execution_time_seconds: Optional[float] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

    def _ensure_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        if self._loop and self._loop.is_running():
            return self._loop
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        return self._loop

    def publish_sync(self, event: InvestigationEvent) -> None:
        """Publish an event synchronously from LangGraph execution or background workers."""
        self._events.append(event)

        if event.event_type == EventType.INVESTIGATION_STARTED:
            self.status = "RUNNING"
        elif event.event_type == EventType.INVESTIGATION_COMPLETED:
            self.status = "COMPLETED"
            self.execution_time_seconds = round(time.time() - self.start_time, 2)
        elif event.event_type == EventType.INVESTIGATION_MAX_ITERATIONS:
            self.status = "MAX_ITERATIONS_REACHED"
            self.execution_time_seconds = round(time.time() - self.start_time, 2)
        elif event.event_type == EventType.INVESTIGATION_FAILED:
            self.status = "FAILED"
            self.execution_time_seconds = round(time.time() - self.start_time, 2)

        loop = self._ensure_loop()
        if loop and loop.is_running():
            loop.call_soon_threadsafe(self._dispatch_to_subscribers, event)
        else:
            self._dispatch_to_subscribers(event)

    def _dispatch_to_subscribers(self, event: Optional[InvestigationEvent]) -> None:
        """Internal dispatch of an event to all active subscriber queues."""
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except Exception as exc:
                logger.debug(f"[EventBus {self.investigation_id}] Subscriber dispatch error: {exc}")

    async def subscribe(
        self, heartbeat_interval: Optional[float] = None
    ) -> AsyncIterator[Optional[InvestigationEvent]]:
        """Subscribe to this investigation's event stream.

        First replays all previously captured events, then yields live events
        as they occur until investigation conclusion.
        If heartbeat_interval is provided, yields None if no event occurs within the interval.
        """
        self._ensure_loop()
        queue: asyncio.Queue[Optional[InvestigationEvent]] = asyncio.Queue()

        # Replay existing events in historical sequence
        for evt in list(self._events):
            await queue.put(evt)

        # If investigation is already in terminal state, signal immediate termination after replay
        if self.status in ("COMPLETED", "FAILED", "MAX_ITERATIONS_REACHED"):
            await queue.put(None)
        else:
            self._subscribers.add(queue)

        try:
            while True:
                if heartbeat_interval and heartbeat_interval > 0:
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
                    except asyncio.TimeoutError:
                        yield None
                        continue
                else:
                    item = await queue.get()

                if item is None:
                    break
                yield item
                if item.event_type in (
                    EventType.INVESTIGATION_COMPLETED,
                    EventType.INVESTIGATION_FAILED,
                    EventType.INVESTIGATION_MAX_ITERATIONS,
                ):
                    break
        finally:
            self._subscribers.discard(queue)

    def set_result(self, report: InvestigationReport, markdown: str) -> None:
        """Store the final compiled report and mark status as COMPLETED."""
        self.report = report
        self.markdown = markdown
        self.status = "COMPLETED"
        if not self.execution_time_seconds:
            self.execution_time_seconds = round(time.time() - self.start_time, 2)

    def set_partial_result(self, report: InvestigationReport, markdown: str) -> None:
        """Store partial report and mark status as MAX_ITERATIONS_REACHED."""
        self.report = report
        self.markdown = markdown
        self.status = "MAX_ITERATIONS_REACHED"
        if not self.execution_time_seconds:
            self.execution_time_seconds = round(time.time() - self.start_time, 2)

    def set_error(self, error: str) -> None:
        """Store error message and mark status as FAILED."""
        self.error = error
        self.status = "FAILED"
        if not self.execution_time_seconds:
            self.execution_time_seconds = round(time.time() - self.start_time, 2)

    def close(self) -> None:
        """Close subscriber streams and discard listeners."""
        loop = self._ensure_loop()
        if loop and loop.is_running():
            loop.call_soon_threadsafe(self._dispatch_to_subscribers, None)
        else:
            self._dispatch_to_subscribers(None)
        self._subscribers.clear()

    @property
    def latest_event(self) -> Optional[InvestigationEvent]:
        """Return the most recently emitted event."""
        return self._events[-1] if self._events else None

    @property
    def events(self) -> List[InvestigationEvent]:
        """Return a copy of the ordered events list."""
        return list(self._events)


class InvestigationEventManager:
    """Thread-safe manager maintaining isolated event buses keyed by investigation ID."""

    def __init__(self):
        self._buses: Dict[str, InvestigationEventBus] = {}

    def get_or_create_bus(self, investigation_id: str) -> InvestigationEventBus:
        """Retrieve existing event bus or instantiate a new isolated bus for this investigation."""
        if investigation_id not in self._buses:
            self._buses[investigation_id] = InvestigationEventBus(investigation_id)
        return self._buses[investigation_id]

    def get_bus(self, investigation_id: str) -> Optional[InvestigationEventBus]:
        """Retrieve event bus for investigation if it exists."""
        return self._buses.get(investigation_id)

    def remove_bus(self, investigation_id: str) -> None:
        """Clean up and remove an investigation bus."""
        bus = self._buses.pop(investigation_id, None)
        if bus:
            bus.close()

    def clear(self) -> None:
        """Remove all active buses (useful for test resets)."""
        for bus in self._buses.values():
            bus.close()
        self._buses.clear()


# Global singleton instance for application lifetime
_manager_instance: Optional[InvestigationEventManager] = None


def get_event_manager() -> InvestigationEventManager:
    """Obtain or initialize the application-level InvestigationEventManager singleton."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = InvestigationEventManager()
    return _manager_instance
