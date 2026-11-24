from __future__ import annotations

import pytest
import asyncio
from app.tools.base import ToolResult
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool, CreateDirectoryTool


@pytest.mark.asyncio
async def test_list_files():
    tool = ListFilesTool()
    result = await tool.execute(path="/tmp")
    assert result.success
    assert "entries" in result.output


@pytest.mark.asyncio
async def test_list_files_nonexistent():
    tool = ListFilesTool()
    result = await tool.execute(path="/nonexistent_path_xyz")
    assert not result.success
    assert result.error is not None


@pytest.mark.asyncio
async def test_read_file():
    tool = ReadFileTool()
    result = await tool.execute(path="/etc/hostname")
    assert result.success
    assert "content" in result.output


@pytest.mark.asyncio
async def test_read_file_nonexistent():
    tool = ReadFileTool()
    result = await tool.execute(path="/nonexistent_file_xyz.txt")
    assert not result.success


@pytest.mark.asyncio
async def test_write_and_read_file():
    import tempfile, os
    tmp = tempfile.mktemp(suffix=".txt")
    try:
        writer = WriteFileTool()
        result = await writer.execute(path=tmp, content="hello indra")
        assert result.success

        reader = ReadFileTool()
        result = await reader.execute(path=tmp)
        assert result.success
        assert "hello indra" in result.output["content"]
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@pytest.mark.asyncio
async def test_create_directory():
    import tempfile, os
    tmp = tempfile.mkdtemp()
    new_dir = os.path.join(tmp, "test_subdir")
    try:
        tool = CreateDirectoryTool()
        result = await tool.execute(path=new_dir)
        assert result.success
        assert os.path.isdir(new_dir)
    finally:
        os.rmdir(new_dir)
        os.rmdir(tmp)
