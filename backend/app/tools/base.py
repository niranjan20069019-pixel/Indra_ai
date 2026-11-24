from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    READ_ONLY = "read_only"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolResult:
    success: bool
    output: Any
    error: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"success": self.success, "output": self.output}
        if self.error:
            d["error"] = self.error
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class ToolMeta:
    name: str
    description: str
    parameters: dict[str, Any]
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    tags: list[str] = field(default_factory=list)


class BaseTool(ABC):
    @property
    @abstractmethod
    def meta(self) -> ToolMeta: ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult: ...

    async def validate_args(self, **kwargs: Any) -> str | None:
        """Return error message if invalid, None if OK."""
        return None

    async def confirm_prompt(self, **kwargs: Any) -> str | None:
        """Return confirmation message if confirmation needed, None otherwise."""
        if self.meta.requires_confirmation:
            return f"About to execute: {self.meta.name}. Confirm?"
        return None
