from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.llm.base import Message, Role


@dataclass
class ConversationContext:
    session_id: str
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    current_project: str | None = None
    current_task: str | None = None

    def add_user_message(self, content: str) -> None:
        self.messages.append(Message(role=Role.USER, content=content))

    def add_assistant_message(self, content: str) -> None:
        self.messages.append(Message(role=Role.ASSISTANT, content=content))

    def add_tool_result(self, tool_call_id: str, name: str, content: str) -> None:
        self.messages.append(
            Message(role=Role.TOOL, content=content, tool_call_id=tool_call_id, name=name)
        )

    def add_system_message(self, content: str) -> None:
        self.messages.append(Message(role=Role.SYSTEM, content=content))

    def get_messages_for_llm(self, max_history: int = 50) -> list[Message]:
        system_msgs = [m for m in self.messages if m.role == Role.SYSTEM]
        other_msgs = [m for m in self.messages if m.role != Role.SYSTEM]
        recent = other_msgs[-max_history:] if len(other_msgs) > max_history else other_msgs
        return system_msgs + recent

    def clear(self) -> None:
        self.messages.clear()
        self.current_project = None
        self.current_task = None


class ContextManager:
    def __init__(self) -> None:
        self._sessions: dict[str, ConversationContext] = {}

    def get_or_create(self, session_id: str) -> ConversationContext:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationContext(session_id=session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> ConversationContext | None:
        return self._sessions.get(session_id)

    def close(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
