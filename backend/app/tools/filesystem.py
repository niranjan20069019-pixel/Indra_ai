from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import structlog

from app.core.security import is_path_safe
from app.tools.base import BaseTool, RiskLevel, ToolMeta, ToolResult

logger = structlog.get_logger("tools.filesystem")


class ListFilesTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="list_files",
            description="List files and directories at a given path.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list"},
                    "recursive": {"type": "boolean", "description": "List recursively", "default": False},
                },
                "required": ["path"],
            },
            risk_level=RiskLevel.READ_ONLY,
            tags=["filesystem", "read"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = Path(kwargs["path"]).expanduser().resolve()
        recursive = kwargs.get("recursive", False)

        if not path.exists():
            return ToolResult(success=False, output=None, error=f"Path does not exist: {path}")
        if not path.is_dir():
            return ToolResult(success=False, output=None, error=f"Not a directory: {path}")

        try:
            if recursive:
                entries = []
                for root, dirs, files in os.walk(path):
                    for name in dirs + files:
                        full = Path(root) / name
                        rel = full.relative_to(path)
                        entries.append(str(rel))
                    if len(entries) > 500:
                        entries.append("... (truncated)")
                        break
            else:
                entries = sorted(os.listdir(path))

            return ToolResult(success=True, output={"path": str(path), "entries": entries})
        except PermissionError:
            return ToolResult(success=False, output=None, error=f"Permission denied: {path}")


class ReadFileTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="read_file",
            description="Read the contents of a text file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "max_lines": {"type": "integer", "description": "Max lines to read", "default": 500},
                },
                "required": ["path"],
            },
            risk_level=RiskLevel.READ_ONLY,
            tags=["filesystem", "read"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = Path(kwargs["path"]).expanduser().resolve()
        max_lines = kwargs.get("max_lines", 500)

        if not path.exists():
            return ToolResult(success=False, output=None, error=f"File does not exist: {path}")
        if not path.is_file():
            return ToolResult(success=False, output=None, error=f"Not a file: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"... (truncated at {max_lines} lines)")
                        break
                    lines.append(line)

            content = "".join(lines)
            return ToolResult(
                success=True,
                output={"path": str(path), "content": content, "lines": len(lines)},
            )
        except PermissionError:
            return ToolResult(success=False, output=None, error=f"Permission denied: {path}")


class WriteFileTool(BaseTool):
    def __init__(self, approved_workspaces: list[str] | None = None):
        self._approved = approved_workspaces

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="write_file",
            description="Write content to a file. Creates or overwrites.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
            risk_level=RiskLevel.MODERATE,
            tags=["filesystem", "write"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = Path(kwargs["path"]).expanduser().resolve()
        content = kwargs["content"]

        if not is_path_safe(str(path), self._approved):
            return ToolResult(
                success=False, output=None,
                error=f"Path not in approved workspaces: {path}",
            )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            logger.info("file_written", path=str(path), size=len(content))
            return ToolResult(success=True, output={"path": str(path), "bytes": len(content)})
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CreateDirectoryTool(BaseTool):
    def __init__(self, approved_workspaces: list[str] | None = None):
        self._approved = approved_workspaces

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="create_directory",
            description="Create a directory and any necessary parent directories.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create"},
                },
                "required": ["path"],
            },
            risk_level=RiskLevel.LOW,
            tags=["filesystem", "write"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = Path(kwargs["path"]).expanduser().resolve()

        if not is_path_safe(str(path), self._approved):
            return ToolResult(
                success=False, output=None,
                error=f"Path not in approved workspaces: {path}",
            )

        try:
            path.mkdir(parents=True, exist_ok=True)
            return ToolResult(success=True, output={"path": str(path), "created": True})
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
