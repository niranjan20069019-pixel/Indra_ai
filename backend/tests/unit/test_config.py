from __future__ import annotations

import pytest
from app.core.config import get_settings


def test_settings_loads():
    settings = get_settings()
    assert settings.llm_provider in ("ollama", "openai", "anthropic")
    assert settings.api_port == 8420
    assert settings.database_url.startswith("sqlite+aiosqlite:///")


def test_approved_workspace_list():
    settings = get_settings()
    result = settings.approved_workspace_list
    assert isinstance(result, list)
