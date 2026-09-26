"""Real-time event architecture for the AML Investigation Copilot."""

from aml_copilot.events.bus import (
    InvestigationEventBus,
    InvestigationEventManager,
    get_event_manager,
)
from aml_copilot.events.models import EventType, InvestigationEvent

__all__ = [
    "EventType",
    "InvestigationEvent",
    "InvestigationEventBus",
    "InvestigationEventManager",
    "get_event_manager",
]
