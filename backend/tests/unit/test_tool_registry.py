from __future__ import annotations

import pytest
from app.tools.base import BaseTool, RiskLevel, ToolMeta, ToolResult
from app.tools.registry import ToolRegistry, get_tool_registry


class MockTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="mock_tool",
            description="A mock tool",
            parameters={"type": "object", "properties": {}},
            risk_level=RiskLevel.LOW,
        )

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, output="mock output")


def test_tool_registry_register():
    registry = ToolRegistry()
    tool = MockTool()
    registry.register(tool)
    assert registry.count() == 1
    assert registry.get("mock_tool") is tool


def test_tool_registry_list():
    registry = ToolRegistry()
    tool = MockTool()
    registry.register(tool)
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "mock_tool"


def test_tool_registry_unregister():
    registry = ToolRegistry()
    tool = MockTool()
    registry.register(tool)
    assert registry.count() == 1
    registry.unregister("mock_tool")
    assert registry.count() == 0
    assert registry.get("mock_tool") is None


def test_tool_definitions_for_llm():
    registry = ToolRegistry()
    tool = MockTool()
    registry.register(tool)
    defs = registry.get_definitions_for_llm()
    assert len(defs) == 1
    assert defs[0].name == "mock_tool"
