from __future__ import annotations

import pytest
import asyncio
from app.tools.terminal import TerminalTool
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_terminal_simple_command():
    tool = TerminalTool()
    result = await tool.execute(command="echo hello")
    assert result.success
    assert "hello" in result.output["stdout"]


@pytest.mark.asyncio
async def test_terminal_denied_command():
    tool = TerminalTool()
    result = await tool.execute(command="rm -rf /")
    assert not result.success
    assert "blocked" in result.error.lower()


@pytest.mark.asyncio
async def test_terminal_nonexistent_command():
    tool = TerminalTool()
    result = await tool.execute(command="nonexistent_command_xyz")
    assert not result.success
