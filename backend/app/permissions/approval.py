from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.core.events import EventType, emit_event

logger = structlog.get_logger("permissions.approval")


class ConfirmationManager:
    def __init__(self) -> None:
        self._pending: dict[str, dict[str, Any]] = {}

    async def request_confirmation(
        self,
        tool_name: str,
        args: dict[str, Any],
        prompt: str,
    ) -> str:
        request_id = str(uuid.uuid4())
        self._pending[request_id] = {
            "tool_name": tool_name,
            "args": args,
            "prompt": prompt,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }

        await emit_event(
            EventType.CONFIRMATION_REQUESTED,
            data={"request_id": request_id, "tool": tool_name, "prompt": prompt},
        )

        logger.info("confirmation_requested", request_id=request_id, tool=tool_name)
        return request_id

    async def approve(self, request_id: str) -> bool:
        req = self._pending.get(request_id)
        if not req:
            return False
        req["status"] = "approved"
        await emit_event(
            EventType.CONFIRMATION_APPROVED,
            data={"request_id": request_id, "tool": req["tool_name"]},
        )
        return True

    async def deny(self, request_id: str) -> bool:
        req = self._pending.get(request_id)
        if not req:
            return False
        req["status"] = "denied"
        await emit_event(
            EventType.CONFIRMATION_DENIED,
            data={"request_id": request_id, "tool": req["tool_name"]},
        )
        return True

    def get_pending(self, request_id: str) -> dict[str, Any] | None:
        return self._pending.get(request_id)

    def cleanup(self) -> None:
        expired = [
            k for k, v in self._pending.items()
            if v["status"] != "pending"
        ]
        for k in expired:
            del self._pending[k]


_confirmation_manager: ConfirmationManager | None = None


def get_confirmation_manager() -> ConfirmationManager:
    global _confirmation_manager
    if _confirmation_manager is None:
        _confirmation_manager = ConfirmationManager()
    return _confirmation_manager
