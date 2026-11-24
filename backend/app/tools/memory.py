from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import Memory, get_session
from app.tools.base import BaseTool, RiskLevel, ToolMeta, ToolResult

logger = structlog.get_logger("tools.memory")


class SaveMemoryTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="save_memory",
            description="Save an important piece of information to long-term memory.",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "What to remember"},
                    "category": {"type": "string", "description": "Category (preference, fact, project, personal, general)", "default": "general"},
                    "importance": {"type": "number", "description": "Importance 0.0-1.0", "default": 0.5},
                    "tags": {"type": "string", "description": "Comma-separated tags"},
                },
                "required": ["content"],
            },
            risk_level=RiskLevel.LOW,
            tags=["memory", "write"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        content = kwargs["content"]
        category = kwargs.get("category", "general")
        importance = kwargs.get("importance", 0.5)
        tags = kwargs.get("tags", "")

        async for session in get_session():
            memory = Memory(
                content=content, category=category,
                importance=importance, tags=tags,
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            logger.info("memory_saved", memory_id=memory.id, category=category)
            return ToolResult(
                success=True,
                output={"id": memory.id, "content": content, "category": category},
            )
        return ToolResult(success=False, output=None, error="Database session failed")


class SearchMemoryTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="search_memory",
            description="Search long-term memory for relevant information.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "category": {"type": "string", "description": "Filter by category"},
                    "limit": {"type": "integer", "description": "Max results", "default": 10},
                },
                "required": ["query"],
            },
            risk_level=RiskLevel.READ_ONLY,
            tags=["memory", "read"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs["query"]
        category = kwargs.get("category")
        limit = kwargs.get("limit", 10)

        async for session in get_session():
            stmt = select(Memory)
            if category:
                stmt = stmt.where(Memory.category == category)
            stmt = stmt.order_by(Memory.importance.desc(), Memory.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            memories = result.scalars().all()

            query_lower = query.lower()
            scored = []
            for m in memories:
                score = sum(1 for word in query_lower.split() if word in m.content.lower())
                scored.append((score, m))
            scored.sort(key=lambda x: (-x[0], -x[1].importance))

            output = [
                {
                    "id": m.id,
                    "content": m.content,
                    "category": m.category,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for _, m in scored[:limit]
            ]
            return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=None, error="Database session failed")


class DeleteMemoryTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="delete_memory",
            description="Delete a memory entry.",
            parameters={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "integer", "description": "Memory ID to delete"},
                },
                "required": ["memory_id"],
            },
            risk_level=RiskLevel.MODERATE,
            requires_confirmation=True,
            tags=["memory", "delete"],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        memory_id = kwargs["memory_id"]

        async for session in get_session():
            result = await session.execute(select(Memory).where(Memory.id == memory_id))
            memory = result.scalar_one_or_none()
            if not memory:
                return ToolResult(success=False, output=None, error=f"Memory {memory_id} not found")

            await session.execute(delete(Memory).where(Memory.id == memory_id))
            await session.commit()
            logger.info("memory_deleted", memory_id=memory_id)
            return ToolResult(success=True, output={"memory_id": memory_id, "deleted": True})
        return ToolResult(success=False, output=None, error="Database session failed")
