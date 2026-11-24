from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceStatus(BaseModel):
    stt: str
    tts: str
    enabled: bool


@router.get("/status", response_model=VoiceStatus)
async def voice_status():
    settings = get_settings()
    return VoiceStatus(
        stt="configured" if settings.voice_enabled else "disabled",
        tts="configured" if settings.voice_enabled else "disabled",
        enabled=settings.voice_enabled,
    )


@router.post("/start-listening")
async def start_listening():
    return {"status": "not_implemented", "message": "Voice input coming in Phase 11"}


@router.post("/stop-listening")
async def stop_listening():
    return {"status": "not_implemented", "message": "Voice input coming in Phase 11"}
