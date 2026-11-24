from __future__ import annotations

from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.database.database import init_database
from app.api import api_router
from app.tools import register_all_tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    log = get_logger("main")
    log.info("starting_indra", version="0.1.0")

    await init_database(settings.database_url)
    log.info("database_initialized")

    register_all_tools()
    from app.tools.registry import get_tool_registry
    registry = get_tool_registry()
    log.info("tools_registered", count=registry.count())

    yield

    from app.llm.factory import close_llm_provider
    await close_llm_provider()
    log.info("shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="INDRA AI",
        description="Local-first personal AI assistant",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url, "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "indra-ai"}

    return app


app = create_app()


def main():
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
