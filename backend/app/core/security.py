from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

from app.core.config import get_settings


def is_path_safe(path: str, approved: list[str] | None = None) -> bool:
    if approved is None:
        approved = get_settings().approved_workspace_list
    if not approved:
        return True
    resolved = Path(path).resolve()
    return any(resolved.is_relative_to(Path(a).resolve()) for a in approved)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_sensitive(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def mask_secret(value: str, visible_chars: int = 4) -> str:
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars)
