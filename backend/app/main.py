import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.analysis.manager import AnalysisManager, stop_analysis_manager
from app.db import Base, SessionFactory, close_database, engine
from app.errors import (
    BackendError,
    backend_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from app.events import EventBroker
from app.routers import agents, analysis, events, export, graph, health, providers, research, workspace


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.event_broker = EventBroker(session_factory=SessionFactory)
    app.state.analysis_manager = AnalysisManager(app.state.event_broker)
    await app.state.analysis_manager.recover()
    yield
    await stop_analysis_manager(app.state.analysis_manager)
    await close_database()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.api_version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    app.add_exception_handler(BackendError, backend_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
    prefix = f"/api/{settings.api_version}"
    app.include_router(health.router, prefix=prefix)
    app.include_router(providers.router, prefix=prefix)
    app.include_router(agents.router, prefix=prefix)
    app.include_router(events.router, prefix=prefix)
    app.include_router(research.router, prefix=prefix)
    app.include_router(analysis.router, prefix=prefix)
    app.include_router(workspace.router, prefix=prefix)
    app.include_router(graph.router, prefix=prefix)
    app.include_router(export.router, prefix=prefix)
    return app


app = create_app()
