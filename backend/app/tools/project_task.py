from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import Project, Task, get_session
from app.tools.base import BaseTool, RiskLevel, ToolMeta, ToolResult

logger = structlog.get_logger("tools.projects")


class ListProjectsTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="list_projects",
            description="List all projects with their status and progress.",
            parameters={"type": "object", "properties": {}},
            risk_level=RiskLevel.READ_ONLY,
            tags=["projects", "read"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        async for session in get_session():
            result = await session.execute(select(Project).order_by(Project.priority.desc()))
            projects = result.scalars().all()
            output = [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "priority": p.priority,
                    "deadline": p.deadline.isoformat() if p.deadline else None,
                    "progress": p.progress,
                }
                for p in projects
            ]
            return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=None, error="Database session failed")


class CreateProjectTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="create_project",
            description="Create a new project.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                    "description": {"type": "string", "description": "Project description"},
                    "priority": {"type": "integer", "description": "Priority (0-10)", "default": 0},
                    "deadline": {"type": "string", "description": "Deadline in ISO format"},
                },
                "required": ["name"],
            },
            risk_level=RiskLevel.LOW,
            tags=["projects", "write"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from datetime import datetime, timezone
        name = kwargs["name"]
        description = kwargs.get("description", "")
        priority = kwargs.get("priority", 0)
        deadline_str = kwargs.get("deadline")

        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str)
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
            except ValueError:
                return ToolResult(success=False, output=None, error=f"Invalid deadline format: {deadline_str}")

        async for session in get_session():
            existing = await session.execute(select(Project).where(Project.name == name))
            if existing.scalar_one_or_none():
                return ToolResult(success=False, output=None, error=f"Project '{name}' already exists")

            project = Project(
                name=name, description=description,
                priority=priority, deadline=deadline,
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            logger.info("project_created", project_id=project.id, name=name)
            return ToolResult(
                success=True,
                output={"id": project.id, "name": name, "status": "active"},
            )
        return ToolResult(success=False, output=None, error="Database session failed")


class UpdateProjectTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="update_project",
            description="Update a project's fields (name, description, status, priority, deadline, progress).",
            parameters={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Project ID"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string", "description": "active, completed, paused, archived"},
                    "priority": {"type": "integer"},
                    "deadline": {"type": "string", "description": "ISO format datetime"},
                    "progress": {"type": "number", "description": "0.0 to 100.0"},
                },
                "required": ["project_id"],
            },
            risk_level=RiskLevel.LOW,
            tags=["projects", "write"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from datetime import datetime, timezone
        project_id = kwargs.pop("project_id")
        updates = {k: v for k, v in kwargs.items() if v is not None}

        if "deadline" in updates and updates["deadline"]:
            try:
                updates["deadline"] = datetime.fromisoformat(updates["deadline"])
                if updates["deadline"].tzinfo is None:
                    updates["deadline"] = updates["deadline"].replace(tzinfo=timezone.utc)
            except ValueError:
                return ToolResult(success=False, output=None, error="Invalid deadline format")

        async for session in get_session():
            await session.execute(update(Project).where(Project.id == project_id).values(**updates))
            await session.commit()
            logger.info("project_updated", project_id=project_id, fields=list(updates.keys()))
            return ToolResult(success=True, output={"project_id": project_id, "updated_fields": list(updates.keys())})
        return ToolResult(success=False, output=None, error="Database session failed")


class ListTasksTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="list_tasks",
            description="List tasks, optionally filtered by project or status.",
            parameters={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Filter by project"},
                    "status": {"type": "string", "description": "Filter by status (pending, completed)"},
                },
            },
            risk_level=RiskLevel.READ_ONLY,
            tags=["tasks", "read"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        async for session in get_session():
            query = select(Task)
            if "project_id" in kwargs and kwargs["project_id"] is not None:
                query = query.where(Task.project_id == kwargs["project_id"])
            if "status" in kwargs and kwargs["status"] is not None:
                query = query.where(Task.status == kwargs["status"])
            query = query.order_by(Task.priority.desc(), Task.due_date.asc().nullslast())
            result = await session.execute(query)
            tasks = result.scalars().all()
            output = [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "project_id": t.project_id,
                    "tags": t.tags,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                }
                for t in tasks
            ]
            return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=None, error="Database session failed")


class CreateTaskTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="create_task",
            description="Create a new task.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {"type": "integer", "description": "Priority (0-10)", "default": 0},
                    "due_date": {"type": "string", "description": "Due date in ISO format"},
                    "project_id": {"type": "integer", "description": "Associated project ID"},
                    "tags": {"type": "string", "description": "Comma-separated tags"},
                },
                "required": ["title"],
            },
            risk_level=RiskLevel.LOW,
            tags=["tasks", "write"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from datetime import datetime, timezone
        title = kwargs["title"]
        description = kwargs.get("description", "")
        priority = kwargs.get("priority", 0)
        project_id = kwargs.get("project_id")
        tags = kwargs.get("tags", "")
        due_date_str = kwargs.get("due_date")

        due_date = None
        if due_date_str:
            try:
                due_date = datetime.fromisoformat(due_date_str)
                if due_date.tzinfo is None:
                    due_date = due_date.replace(tzinfo=timezone.utc)
            except ValueError:
                return ToolResult(success=False, output=None, error="Invalid due_date format")

        async for session in get_session():
            task = Task(
                title=title, description=description, priority=priority,
                project_id=project_id, tags=tags, due_date=due_date,
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            logger.info("task_created", task_id=task.id, title=title)
            return ToolResult(success=True, output={"id": task.id, "title": title, "status": "pending"})
        return ToolResult(success=False, output=None, error="Database session failed")


class CompleteTaskTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="complete_task",
            description="Mark a task as completed.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID to complete"},
                },
                "required": ["task_id"],
            },
            risk_level=RiskLevel.LOW,
            tags=["tasks", "write"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from datetime import datetime, timezone
        task_id = kwargs["task_id"]

        async for session in get_session():
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return ToolResult(success=False, output=None, error=f"Task {task_id} not found")

            await session.execute(
                update(Task).where(Task.id == task_id).values(
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
            logger.info("task_completed", task_id=task_id)
            return ToolResult(success=True, output={"task_id": task_id, "title": task.title, "status": "completed"})
        return ToolResult(success=False, output=None, error="Database session failed")


class DeleteTaskTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="delete_task",
            description="Delete a task. This requires confirmation.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID to delete"},
                },
                "required": ["task_id"],
            },
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            tags=["tasks", "delete"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        task_id = kwargs["task_id"]

        async for session in get_session():
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return ToolResult(success=False, output=None, error=f"Task {task_id} not found")

            await session.execute(delete(Task).where(Task.id == task_id))
            await session.commit()
            logger.info("task_deleted", task_id=task_id)
            return ToolResult(success=True, output={"task_id": task_id, "deleted": True})
        return ToolResult(success=False, output=None, error="Database session failed")
