from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.tools.base import BaseTool, RiskLevel, ToolMeta, ToolResult

logger = structlog.get_logger("tools.web_search")


class WebSearchTool(BaseTool):
    def __init__(self, provider: str = "duckduckgo"):
        self._provider = provider
        self._client = httpx.AsyncClient(timeout=15.0)

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="web_search",
            description="Search the internet for current information on a topic.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "description": "Number of results", "default": 5},
                },
                "required": ["query"],
            },
            risk_level=RiskLevel.READ_ONLY,
            tags=["web", "search"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs["query"]
        num_results = kwargs.get("num_results", 5)

        if self._provider == "duckduckgo":
            return await self._search_duckduckgo(query, num_results)
        return ToolResult(success=False, output=None, error=f"Unknown search provider: {self._provider}")

    async def _search_duckduckgo(self, query: str, num_results: int) -> ToolResult:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return ToolResult(
                success=False, output=None,
                error="duckduckgo-search not installed. Run: pip install duckduckgo-search",
            )

        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })

            return ToolResult(success=True, output={"query": query, "results": results})
        except Exception as e:
            logger.error("search_error", query=query, error=str(e))
            return ToolResult(success=False, output=None, error=f"Search failed: {e}")

    async def close(self) -> None:
        await self._client.aclose()
