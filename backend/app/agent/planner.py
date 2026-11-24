from __future__ import annotations

import json
from typing import Any

import structlog

from app.llm.base import LLMProvider, Message, Role, ToolDefinition
from app.tools.base import ToolResult

logger = structlog.get_logger("agent.tool_selector")

SYSTEM_PROMPT = """You are INDRA, a capable, intelligent, and helpful personal AI assistant.

Core behavior:
- Be concise and direct by default. Only elaborate when the user asks for detail.
- You have access to tools. Use them when they help accomplish the user's request.
- Never fabricate information. If you don't know something, say so.
- Never claim you performed an action unless you actually did.
- For destructive actions (delete, send email, financial), always confirm with the user first.
- You can help with: tasks, projects, memory, file management, web search, coding, terminal commands, documents.
- If a tool fails, explain the failure clearly and suggest alternatives.
- Track conversation context. If the user refers to something earlier, use that context.
- Be proactive but not annoying. Offer help when appropriate.
- Distinguish between: "I can do this", "I am doing this", "I completed this", "I failed at this".

When you need to use a tool, call it with the correct function name and arguments.
When the user asks you to remember something, use the save_memory tool.
When the user asks about their tasks or projects, use the list tools.
For web searches, use the web_search tool.
For file operations, use the filesystem tools.
For running code or commands, use the run_command tool."""


def build_system_message() -> Message:
    return Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)


def parse_tool_calls_from_response(response_text: str) -> list[dict[str, Any]] | None:
    """Try to extract tool calls from text if LLM returns them in markdown format."""
    if "<tool_call>" not in response_text:
        return None
    calls = []
    import re
    pattern = r"<tool_call>(.*?)</tool_call>"
    for match in re.findall(pattern, response_text, re.DOTALL):
        try:
            call = json.loads(match.strip())
            calls.append(call)
        except json.JSONDecodeError:
            continue
    return calls if calls else None
