from __future__ import annotations

from app.core.config import get_settings
from app.tools.registry import get_tool_registry
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool, CreateDirectoryTool
from app.tools.terminal import TerminalTool
from app.tools.web_search import WebSearchTool
from app.tools.project_task import (
    ListProjectsTool, CreateProjectTool, UpdateProjectTool,
    ListTasksTool, CreateTaskTool, CompleteTaskTool, DeleteTaskTool,
)
from app.tools.memory import SaveMemoryTool, SearchMemoryTool, DeleteMemoryTool


def register_all_tools() -> None:
    registry = get_tool_registry()
    settings = get_settings()
    workspaces = settings.approved_workspace_list

    registry.register(ListFilesTool())
    registry.register(ReadFileTool())
    registry.register(WriteFileTool(approved_workspaces=workspaces))
    registry.register(CreateDirectoryTool(approved_workspaces=workspaces))
    registry.register(TerminalTool(allowed_workspaces=workspaces, timeout=settings.terminal_timeout))
    registry.register(WebSearchTool(provider=settings.search_provider))

    registry.register(ListProjectsTool())
    registry.register(CreateProjectTool())
    registry.register(UpdateProjectTool())
    registry.register(ListTasksTool())
    registry.register(CreateTaskTool())
    registry.register(CompleteTaskTool())
    registry.register(DeleteTaskTool())

    registry.register(SaveMemoryTool())
    registry.register(SearchMemoryTool())
    registry.register(DeleteMemoryTool())
