from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger("events")


class EventType(str, Enum):
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    TOOL_INVOKED = "tool.invoked"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    CONFIRMATION_REQUESTED = "confirmation.requested"
    CONFIRMATION_APPROVED = "confirmation.approved"
    CONFIRMATION_DENIED = "confirmation.denied"
    MEMORY_SAVED = "memory.saved"
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    PROJECT_CREATED = "project.created"
    CHECKIN_TRIGGERED = "checkin.triggered"
    VOICE_INPUT = "voice.input"
    VOICE_OUTPUT = "voice.output"
    ERROR = "error"


async def emit_event(
    event_type: EventType,
    data: dict[str, Any] | None = None,
    *,
    source: str = "system",
) -> None:
    payload = {
        "event": event_type.value,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data or {},
    }
    logger.info("event_emitted", **payload)
