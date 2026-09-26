"""Unit tests for the real-time Investigation Event models and EventBus."""

import asyncio
import pytest

from aml_copilot.events.bus import InvestigationEventBus, InvestigationEventManager
from aml_copilot.events.models import EventType, InvestigationEvent


def test_investigation_event_model_creation():
    """Verify strongly typed creation and defaults of InvestigationEvent."""
    evt = InvestigationEvent(
        investigation_id="INV-TEST-001",
        event_type=EventType.NODE_STARTED,
        node="investigator",
        message="Investigator reasoning initiated.",
        iteration=1,
        metadata={"model": "gpt-4o"},
    )
    assert evt.event_id.startswith("evt_")
    assert evt.investigation_id == "INV-TEST-001"
    assert evt.event_type == "NODE_STARTED"
    assert evt.node == "investigator"
    assert evt.iteration == 1
    assert evt.metadata["model"] == "gpt-4o"
    assert "T" in evt.timestamp  # Valid ISO timestamp

    # JSON serialization
    serialized = evt.model_dump_json()
    assert "INV-TEST-001" in serialized
    assert "NODE_STARTED" in serialized


def test_investigation_event_bus_isolation():
    """Verify two independent investigation event buses do not leak events to each other."""
    manager = InvestigationEventManager()
    bus_a = manager.get_or_create_bus("INV-A")
    bus_b = manager.get_or_create_bus("INV-B")

    evt_a = InvestigationEvent(
        investigation_id="INV-A",
        event_type=EventType.INVESTIGATION_STARTED,
        message="Case A started.",
    )
    evt_b = InvestigationEvent(
        investigation_id="INV-B",
        event_type=EventType.INVESTIGATION_STARTED,
        message="Case B started.",
    )

    bus_a.publish_sync(evt_a)
    bus_b.publish_sync(evt_b)

    assert len(bus_a.events) == 1
    assert bus_a.events[0].investigation_id == "INV-A"
    assert len(bus_b.events) == 1
    assert bus_b.events[0].investigation_id == "INV-B"

    # Remove bus
    manager.remove_bus("INV-A")
    assert manager.get_bus("INV-A") is None
    assert manager.get_bus("INV-B") is not None


def test_event_bus_subscription_and_replay():
    """Verify subscriber receives past events upon connection plus subsequent live events."""
    async def _run_test():
        bus = InvestigationEventBus("INV-ASYNC-01")

        # 1. Publish prior historical event
        evt1 = InvestigationEvent(
            investigation_id="INV-ASYNC-01",
            event_type=EventType.INVESTIGATION_STARTED,
            message="Event 1 started.",
        )
        bus.publish_sync(evt1)

        received_events = []

        async def consume_events():
            async for event in bus.subscribe():
                received_events.append(event)

        consumer_task = asyncio.create_task(consume_events())
        await asyncio.sleep(0.01)

        # 2. Publish live events
        evt2 = InvestigationEvent(
            investigation_id="INV-ASYNC-01",
            event_type=EventType.NODE_STARTED,
            node="investigator",
            message="Event 2 node started.",
        )
        evt3 = InvestigationEvent(
            investigation_id="INV-ASYNC-01",
            event_type=EventType.INVESTIGATION_COMPLETED,
            message="Event 3 completed.",
        )
        bus.publish_sync(evt2)
        bus.publish_sync(evt3)

        await consumer_task

        assert len(received_events) == 3
        assert received_events[0].event_type == EventType.INVESTIGATION_STARTED
        assert received_events[1].event_type == EventType.NODE_STARTED
        assert received_events[2].event_type == EventType.INVESTIGATION_COMPLETED
        assert bus.status == "COMPLETED"

    asyncio.run(_run_test())


def test_event_bus_lifecycle_state_and_errors():
    """Verify status and error recording on bus."""
    bus = InvestigationEventBus("INV-FAIL-01")
    assert bus.status == "QUEUED"

    bus.publish_sync(
        InvestigationEvent(
            investigation_id="INV-FAIL-01",
            event_type=EventType.INVESTIGATION_STARTED,
            message="Started.",
        )
    )
    assert bus.status == "RUNNING"

    bus.publish_sync(
        InvestigationEvent(
            investigation_id="INV-FAIL-01",
            event_type=EventType.INVESTIGATION_FAILED,
            message="Failed on parsing.",
        )
    )
    assert bus.status == "FAILED"
    assert bus.execution_time_seconds is not None
