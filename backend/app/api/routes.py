from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agent.orchestrator import Orchestrator
from app.tools.registry import get_tool_registry

api_router = Orchestrator._instance = None


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] | None = None
    session_id: str


class StatusResponse(BaseModel):
    status: str
    version: str
    modules: dict[str, str]
    tools_registered: int


_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    orch = get_orchestrator()
    result = await orch.handle_message(
        user_message=request.message,
        session_id=request.session_id,
    )
    return ChatResponse(**result)


@router.get("/status")
async def status():
    registry = get_tool_registry()
    return {
        "status": "online",
        "version": "0.1.0",
        "modules": {
            "llm": "ready",
            "voice": "pending",
            "tools": f"{registry.count()} registered",
            "memory": "ready",
            "projects": "ready",
            "tasks": "ready",
        },
        "tools_registered": registry.count(),
    }


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/tools")
async def list_tools():
    registry = get_tool_registry()
    tools = registry.list_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level.value,
                "tags": t.tags,
            }
            for t in tools
        ]
    }
