from __future__ import annotations

import json
import uuid
from typing import Any

import structlog

from app.agent.context import ContextManager, ConversationContext
from app.agent.planner import build_system_message
from app.core.events import EventType, emit_event
from app.core.logging import get_logger
from app.llm.base import LLMProvider, Message, Role
from app.llm.factory import get_llm_provider
from app.tools.base import ToolResult
from app.tools.registry import ToolRegistry, get_tool_registry

logger = get_logger("agent.orchestrator")

MAX_TOOL_ROUNDS = 10


class Orchestrator:
    def __init__(
        self,
        llm: LLMProvider | None = None,
        registry: ToolRegistry | None = None,
        context_manager: ContextManager | None = None,
    ):
        self._llm = llm
        self._registry = registry or get_tool_registry()
        self._contexts = context_manager or ContextManager()

    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = get_llm_provider()
        return self._llm

    async def handle_message(
        self,
        user_message: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        sid = session_id or str(uuid.uuid4())
        ctx = self._contexts.get_or_create(sid)

        if not ctx.messages:
            ctx.add_system_message(build_system_message().content)

        ctx.add_user_message(user_message)

        await emit_event(
            EventType.AGENT_STARTED,
            data={"session_id": sid, "message": user_message[:200]},
        )

        tools = self._registry.get_definitions_for_llm()
        messages = ctx.get_messages_for_llm()

        all_tool_results: list[dict[str, Any]] = []
        rounds = 0

        try:
            while rounds < MAX_TOOL_ROUNDS:
                rounds += 1
                response = await self.llm.generate(
                    messages=messages,
                    tools=tools if tools else None,
                    temperature=0.7,
                    max_tokens=4096,
                )

                if response.tool_calls:
                    messages.append(
                        Message(
                            role=Role.ASSISTANT,
                            content=response.content or "",
                            tool_calls=response.tool_calls,
                        )
                    )

                    for tc in response.tool_calls:
                        func = tc.get("function", {})
                        tool_name = func.get("name", "")
                        try:
                            tool_args = json.loads(func.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            tool_args = {}

                        logger.info("tool_call", tool=tool_name, args=list(tool_args.keys()))

                        await emit_event(
                            EventType.TOOL_INVOKED,
                            data={"tool": tool_name, "args": tool_args},
                            source="orchestrator",
                        )

                        tool_result = await self._registry.execute(tool_name, **tool_args)

                        result_text = json.dumps(tool_result.to_dict())
                        messages.append(
                            Message(
                                role=Role.TOOL,
                                content=result_text,
                                tool_call_id=tc.get("id", ""),
                                name=tool_name,
                            )
                        )

                        all_tool_results.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "success": tool_result.success,
                            "output": tool_result.output,
                            "error": tool_result.error,
                        })

                        await emit_event(
                            EventType.TOOL_COMPLETED if tool_result.success else EventType.TOOL_FAILED,
                            data={"tool": tool_name, "success": tool_result.success},
                            source="orchestrator",
                        )

                    continue

                if response.content:
                    ctx.add_assistant_message(response.content)

                await emit_event(
                    EventType.AGENT_COMPLETED,
                    data={"session_id": sid, "tool_rounds": rounds},
                )

                return {
                    "reply": response.content or "I don't have a response for that.",
                    "tool_calls": all_tool_results if all_tool_results else None,
                    "session_id": sid,
                }

            return {
                "reply": "I've completed the tool operations. Let me know if you need anything else.",
                "tool_calls": all_tool_results,
                "session_id": sid,
            }

        except ConnectionError as e:
            error_msg = f"I can't connect to the AI model. {e}"
            logger.error("llm_connection_error", error=str(e))
            await emit_event(EventType.ERROR, data={"error": str(e)}, source="orchestrator")
            return {"reply": error_msg, "tool_calls": None, "session_id": sid}

        except Exception as e:
            error_msg = f"An error occurred: {e}"
            logger.error("orchestrator_error", error=str(e))
            await emit_event(EventType.ERROR, data={"error": str(e)}, source="orchestrator")
            return {"reply": error_msg, "tool_calls": None, "session_id": sid}

    def clear_session(self, session_id: str) -> None:
        self._contexts.close(session_id)
