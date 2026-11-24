from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.core.events import EventType, emit_event

logger = structlog.get_logger("automation.scheduler")


class CheckInScheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._enabled = False
        self._callback: Callable[[str], Awaitable[dict[str, Any]]] | None = None

    def set_callback(self, callback: Callable[[str], Awaitable[dict[str, Any]]]) -> None:
        self._callback = callback

    async def start(self) -> None:
        settings = get_settings()
        if not settings.checkin_enabled:
            logger.info("checkins_disabled")
            return

        self._scheduler.add_job(
            self._trigger_checkin,
            IntervalTrigger(minutes=settings.checkin_interval_minutes),
            id="checkin",
            replace_existing=True,
        )
        self._scheduler.start()
        self._enabled = True
        logger.info(
            "scheduler_started",
            interval=settings.checkin_interval_minutes,
            hours=f"{settings.working_hours_start}-{settings.working_hours_end}",
        )

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown()
        self._enabled = False
        logger.info("scheduler_stopped")

    async def _trigger_checkin(self) -> None:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        hour = now.hour

        if not (settings.working_hours_start <= hour < settings.working_hours_end):
            logger.debug("checkin_outside_hours", hour=hour)
            return

        await emit_event(
            EventType.CHECKIN_TRIGGERED,
            data={"time": now.isoformat()},
        )
        logger.info("checkin_triggered")

        if self._callback:
            await self._callback("checkin")

    @property
    def is_running(self) -> bool:
        return self._enabled


_scheduler: CheckInScheduler | None = None


def get_scheduler() -> CheckInScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = CheckInScheduler()
    return _scheduler
