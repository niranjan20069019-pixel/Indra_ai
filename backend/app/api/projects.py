from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import Project, get_session

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    priority: int = 0
    deadline: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    deadline: str | None = None
    progress: float | None = None


@router.get("/")
async def list_projects():
    async for session in get_session():
        result = await session.execute(select(Project).order_by(Project.priority.desc()))
        projects = result.scalars().all()
        return {
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "priority": p.priority,
                    "deadline": p.deadline.isoformat() if p.deadline else None,
                    "progress": p.progress,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in projects
            ]
        }
    return {"projects": []}


@router.post("/")
async def create_project(data: ProjectCreate):
    deadline = None
    if data.deadline:
        try:
            deadline = datetime.fromisoformat(data.deadline)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
        except ValueError:
            return {"error": "Invalid deadline format"}

    async for session in get_session():
        existing = await session.execute(select(Project).where(Project.name == data.name))
        if existing.scalar_one_or_none():
            return {"error": f"Project '{data.name}' already exists"}

        project = Project(
            name=data.name, description=data.description,
            priority=data.priority, deadline=deadline,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "message": "Project created",
        }
    return {"error": "Database error"}


@router.put("/{project_id}")
async def update_project(project_id: int, data: ProjectUpdate):
    updates = data.model_dump(exclude_none=True)
    if "deadline" in updates and updates["deadline"]:
        try:
            updates["deadline"] = datetime.fromisoformat(updates["deadline"])
        except ValueError:
            return {"error": "Invalid deadline format"}

    async for session in get_session():
        await session.execute(update(Project).where(Project.id == project_id).values(**updates))
        await session.commit()
        return {"message": "Project updated", "fields": list(updates.keys())}
    return {"error": "Database error"}


@router.delete("/{project_id}")
async def delete_project(project_id: int):
    async for session in get_session():
        await session.execute(delete(Project).where(Project.id == project_id))
        await session.commit()
        return {"message": "Project deleted", "id": project_id}
    return {"error": "Database error"}
