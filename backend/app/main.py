import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import setup_logging
from app.analysis.manager import AnalysisManager, stop_analysis_manager
from app.db import Base, SessionFactory, close_database, engine
from app.cache.service import cache_service
from app.jobs.worker import worker_service
from app.errors import (
    BackendError,
    backend_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from app.events import EventBroker
from app.analysis.autonomous_workflow_service import autonomous_workflow_service
from app.routers import (
    agents,
    analysis,
    auth,
    autonomous_workflows,
    benchmarks,
    claim_synthesis,
    collaboration,
    contradictions,
    corrections,
    events,
    export,
    gaps,
    graph,
    health,
    hypotheses,
    intelligence,
    invitations,
    jobs,
    methodology_audit,
    providers,
    quality_audit,
    reproducibility,
    research,
    study_independence,
    synthesis,
    trends,
    verification,
    workspace,
    workspaces,
)

# Initialize application logging
setup_logging()
logger = logging.getLogger("neomon.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.event_broker = EventBroker(session_factory=SessionFactory)
    app.state.analysis_manager = AnalysisManager(app.state.event_broker)
    await app.state.analysis_manager.recover()
    autonomous_workflow_service.broker = app.state.event_broker
    await autonomous_workflow_service.recover_workflows()

    if settings.initial_admin_password:
        from app.auth.security import hash_password
        from app.models import User
        from sqlalchemy import select
        async with SessionFactory() as session:
            admin_user = await session.scalar(select(User).where(User.role == "admin").order_by(User.created_at).limit(1))
            if admin_user:
                admin_user.password_hash = hash_password(settings.initial_admin_password)
                await session.commit()
                logger.info("Configured production administrator password from NEOMON_INITIAL_ADMIN_PASSWORD.")

    if settings.worker_enabled:
        await worker_service.start()

    yield

    if settings.worker_enabled:
        await worker_service.stop()
    await cache_service.close()
    await stop_analysis_manager(app.state.analysis_manager)
    await close_database()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.api_version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_and_logging_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = req_id
        start_time = time.time()

        response = await call_next(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id

        # Attach request_id to logging record
        extra = {"request_id": req_id}
        logger.info(
            f"{request.method} {request.url.path} completed with {response.status_code} in {duration_ms}ms",
            extra=extra,
        )
        return response

    app.add_exception_handler(BackendError, backend_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)

    prefix = f"/api/{settings.api_version}"

    # Liveness, readiness, and metrics mounted at both root and /api/v1
    app.include_router(health.router)
    app.include_router(health.router, prefix=prefix)

    # Core API routers
    app.include_router(providers.router, prefix=prefix)
    app.include_router(agents.router, prefix=prefix)
    app.include_router(events.router, prefix=prefix)
    app.include_router(events.router)
    app.include_router(research.router, prefix=prefix)
    app.include_router(analysis.router, prefix=prefix)
    app.include_router(workspace.router, prefix=prefix)
    app.include_router(graph.router, prefix=prefix)
    app.include_router(export.router, prefix=prefix)
    app.include_router(gaps.router, prefix=prefix)
    app.include_router(gaps.router)
    app.include_router(hypotheses.router, prefix=prefix)
    app.include_router(hypotheses.router)
    app.include_router(synthesis.router, prefix=prefix)
    app.include_router(synthesis.router)
    app.include_router(contradictions.router, prefix=prefix)
    app.include_router(contradictions.router)
    app.include_router(trends.router, prefix=prefix)
    app.include_router(trends.router)
    app.include_router(intelligence.router, prefix=prefix)
    app.include_router(intelligence.router)
    app.include_router(quality_audit.router, prefix=prefix)
    app.include_router(quality_audit.router)
    app.include_router(autonomous_workflows.router, prefix=prefix)
    app.include_router(autonomous_workflows.router)

    # M10 & M11 additions
    app.include_router(auth.router)
    app.include_router(workspaces.router)
    app.include_router(invitations.router)
    app.include_router(collaboration.router)
    app.include_router(jobs.router)

    # M12 Scientific Reliability & Reproducibility additions
    app.include_router(verification.router)
    app.include_router(claim_synthesis.router)
    app.include_router(study_independence.router)
    app.include_router(methodology_audit.router)
    app.include_router(reproducibility.router)
    app.include_router(benchmarks.router)
    app.include_router(corrections.router)

    return app


app = create_app()
