from __future__ import annotations

from enum import Enum
from typing import Any

import structlog

from app.tools.base import RiskLevel

logger = structlog.get_logger("permissions")


class PermissionLevel(int, Enum):
    READ_ONLY = 1
    LOW_RISK = 2
    CONFIRM_REQUIRED = 3
    HIGH_SENSITIVE = 4


RISK_TO_PERMISSION: dict[RiskLevel, PermissionLevel] = {
    RiskLevel.READ_ONLY: PermissionLevel.READ_ONLY,
    RiskLevel.LOW: PermissionLevel.LOW_RISK,
    RiskLevel.MODERATE: PermissionLevel.CONFIRM_REQUIRED,
    RiskLevel.HIGH: PermissionLevel.HIGH_SENSITIVE,
    RiskLevel.CRITICAL: PermissionLevel.HIGH_SENSITIVE,
}


class PermissionPolicy:
    def __init__(self, default_level: PermissionLevel = PermissionLevel.CONFIRM_REQUIRED):
        self._default_level = default_level
        self._overrides: dict[str, PermissionLevel] = {}

    def set_override(self, tool_name: str, level: PermissionLevel) -> None:
        self._overrides[tool_name] = level

    def check(self, tool_name: str, risk_level: RiskLevel) -> bool:
        if tool_name in self._overrides:
            required = self._overrides[tool_name]
        else:
            required = RISK_TO_PERMISSION.get(risk_level, self._default_level)
        return required.value <= self._default_level.value

    def requires_confirmation(self, tool_name: str, risk_level: RiskLevel) -> bool:
        if tool_name in self._overrides:
            required = self._overrides[tool_name]
        else:
            required = RISK_TO_PERMISSION.get(risk_level, self._default_level)
        return required.value >= PermissionLevel.CONFIRM_REQUIRED.value


_policy: PermissionPolicy | None = None


def get_permission_policy() -> PermissionPolicy:
    global _policy
    if _policy is None:
        _policy = PermissionPolicy()
    return _policy
