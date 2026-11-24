from __future__ import annotations

import structlog
from typing import Any

from app.tools.base import BaseTool, RiskLevel, ToolMeta, ToolResult
from app.llm.base import ToolDefinition

logger = structlog.get_logger("tools.registry")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        name = tool.meta.name
        if name in self._tools:
            logger.warning("tool_already_registered", name=name)
        self._tools[name] = tool
        logger.debug("tool_registered", name=name, risk=tool.meta.risk_level.value)

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolMeta]:
        return [tool.meta for tool in self._tools.values()]

    def get_definitions_for_llm(self, allowed_risk: RiskLevel = RiskLevel.MODERATE) -> list[ToolDefinition]:
        risk_order = {
            RiskLevel.READ_ONLY: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MODERATE: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }
        max_risk = risk_order.get(allowed_risk, 2)
        definitions: list[ToolDefinition] = []
        for tool in self._tools.values():
            tool_risk = risk_order.get(tool.meta.risk_level, 0)
            if tool_risk <= max_risk:
                definitions.append(
                    ToolDefinition(
                        name=tool.meta.name,
                        description=tool.meta.description,
                        parameters=tool.meta.parameters,
                    )
                )
        return definitions

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(success=False, output=None, error=f"Unknown tool: {name}")

        validation_error = await tool.validate_args(**kwargs)
        if validation_error:
            return ToolResult(success=False, output=None, error=validation_error)

        logger.info("tool_executing", name=name, args=list(kwargs.keys()))
        try:
            result = await tool.execute(**kwargs)
            logger.info("tool_completed", name=name, success=result.success)
            return result
        except Exception as e:
            logger.error("tool_error", name=name, error=str(e))
            return ToolResult(success=False, output=None, error=str(e))

    def count(self) -> int:
        return len(self._tools)


_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
