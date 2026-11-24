from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct-q4_K_M"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Voice
    voice_enabled: bool = False
    stt_model: str = "base"
    stt_device: str = "cpu"
    stt_language: str = "en"
    tts_voice: str = "en_US-lessac-medium"
    tts_speed: float = 1.0
    tts_volume: float = 1.0

    # Search
    search_provider: str = "duckduckgo"
    serpapi_key: str = ""
    tavily_api_key: str = ""

    # Scheduler
    checkin_enabled: bool = True
    checkin_interval_minutes: int = 30
    working_hours_start: int = 9
    working_hours_end: int = 18

    # Security
    approved_workspaces: str = ""
    terminal_timeout: int = 30
    enable_file_deletion: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/indra.db"

    # Logging
    log_level: str = "INFO"
    log_file: str = "./data/logs/indra.log"

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8420

    # Frontend
    frontend_url: str = "http://localhost:3000"

    @property
    def approved_workspace_list(self) -> list[str]:
        if not self.approved_workspaces:
            return []
        return [w.strip() for w in self.approved_workspaces.split(",") if w.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
