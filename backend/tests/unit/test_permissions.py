from __future__ import annotations

import pytest
from app.permissions.policy import PermissionPolicy, PermissionLevel, get_permission_policy
from app.tools.base import RiskLevel


def test_permission_policy_allows_read():
    policy = PermissionPolicy(PermissionLevel.READ_ONLY)
    assert policy.check("any_tool", RiskLevel.READ_ONLY)
    assert not policy.check("any_tool", RiskLevel.LOW)


def test_permission_policy_allows_moderate():
    policy = PermissionPolicy(PermissionLevel.CONFIRM_REQUIRED)
    assert policy.check("any_tool", RiskLevel.READ_ONLY)
    assert policy.check("any_tool", RiskLevel.LOW)
    assert policy.check("any_tool", RiskLevel.MODERATE)
    assert not policy.check("any_tool", RiskLevel.HIGH)


def test_permission_requires_confirmation():
    policy = PermissionPolicy(PermissionLevel.CONFIRM_REQUIRED)
    assert not policy.requires_confirmation("any_tool", RiskLevel.READ_ONLY)
    assert not policy.requires_confirmation("any_tool", RiskLevel.LOW)
    assert policy.requires_confirmation("any_tool", RiskLevel.MODERATE)
    assert policy.requires_confirmation("any_tool", RiskLevel.HIGH)


def test_override():
    policy = PermissionPolicy(PermissionLevel.LOW_RISK)
    assert policy.check("any_tool", RiskLevel.LOW)
    policy.set_override("restricted_tool", PermissionLevel.CONFIRM_REQUIRED)
    assert not policy.check("restricted_tool", RiskLevel.LOW)
    assert policy.check("other_tool", RiskLevel.LOW)
