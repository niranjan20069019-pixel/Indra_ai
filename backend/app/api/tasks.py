from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select, update, delete

from app.database.database import Task, get_session

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: int = 0
    due_date: str | None = None
    project_id: int | None = None
    tags: str = ""


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    due_date: str | None = None
    tags: str | None = None


@router.get("/")
async def list_tasks(project_id: int | None = None, status: str | None = None):
    async for session in get_session():
        query = select(Task)
        if project_id is not None:
            query = query.where(Task.project_id == project_id)
        if status is not None:
            query = query.where(Task.status == status)
        query = query.order_by(Task.priority.desc(), Task.due_date.asc().nullslast())
        result = await session.execute(query)
        tasks = result.scalars().all()
        return {
            "tasks": [
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
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ]
        }
    return {"tasks": []}


@router.post("/")
async def create_task(data: TaskCreate):
    due_date = None
    if data.due_date:
        try:
            due_date = datetime.fromisoformat(data.due_date)
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
        except ValueError:
            return {"error": "Invalid due_date format"}

    async for session in get_session():
        task = Task(
            title=data.title, description=data.description,
            priority=data.priority, project_id=data.project_id,
            tags=data.tags, due_date=due_date,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "message": "Task created",
        }
    return {"error": "Database error"}


@router.put("/{task_id}")
async def update_task(task_id: int, data: TaskUpdate):
    updates = data.model_dump(exclude_none=True)
    if "due_date" in updates and updates["due_date"]:
        try:
            updates["due_date"] = datetime.fromisoformat(updates["due_date"])
        except ValueError:
            return {"error": "Invalid due_date format"}

    async for session in get_session():
        await session.execute(update(Task).where(Task.id == task_id).values(**updates))
        await session.commit()
        return {"message": "Task updated", "fields": list(updates.keys())}
    return {"error": "Database error"}


@router.post("/{task_id}/complete")
async def complete_task(task_id: int):
    async for session in get_session():
        await session.execute(
            update(Task).where(Task.id == task_id).values(
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
        return {"message": "Task completed", "id": task_id}
    return {"error": "Database error"}


@router.delete("/{task_id}")
async def delete_task(task_id: int):
    async for session in get_session():
        await session.execute(delete(Task).where(Task.id == task_id))
        await session.commit()
        return {"message": "Task deleted", "id": task_id}
    return {"error": "Database error"}
