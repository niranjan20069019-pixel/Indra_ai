from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx
import structlog

from app.llm.base import LLMProvider, LLMResponse, Message, ToolDefinition

logger = structlog.get_logger("llm.cloud")


class CloudProvider(LLMProvider):
    """OpenAI-compatible cloud provider (works with OpenAI, Anthropic via proxy, etc.)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        provider_name: str = "openai",
    ):
        self._api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._provider_name = provider_name
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0,
        )

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for msg in messages:
            d: dict[str, Any] = {"role": msg.role.value, "content": msg.content}
            if msg.tool_calls:
                d["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
            if msg.name:
                d["name"] = msg.name
            converted.append(d)
        return converted

    def _convert_tools(self, tools: list[ToolDefinition] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [t.to_dict() for t in tools]

    async def generate(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        converted_tools = self._convert_tools(tools)
        if converted_tools:
            payload["tools"] = converted_tools
            payload["tool_choice"] = "auto"

        try:
            resp = await self._client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()

            choice = data["choices"][0]
            message = choice["message"]

            tool_calls = None
            if message.get("tool_calls"):
                tool_calls = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    }
                    for tc in message["tool_calls"]
                ]

            return LLMResponse(
                content=message.get("content"),
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason"),
                usage=data.get("usage"),
            )
        except httpx.HTTPStatusError as e:
            logger.error("cloud_http_error", status=e.response.status_code, provider=self._provider_name)
            raise
        except httpx.ConnectError:
            logger.error("cloud_connection_failed", provider=self._provider_name)
            raise ConnectionError(f"Cannot connect to {self._provider_name} API.")

    async def stream(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
        except httpx.ConnectError:
            yield f"[Error: Cannot connect to {self._provider_name} API]"

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/models")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
