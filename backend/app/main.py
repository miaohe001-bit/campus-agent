from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router
from app.api.applications import router as applications_router
from app.api.campaigns import router as campaigns_router
from app.api.email_imports import router as email_imports_router
from app.api.events import router as events_router
from app.api.goals import router as goals_router
from app.api.monitoring import router as monitoring_router
from app.api.notifications import router as notifications_router
from app.api.routes import router
from app.api.schedules import router as schedules_router
from app.api.todos import router as todos_router
from app.core.config import settings
from app.runtime.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(title="Campus Agent API", lifespan=lifespan)
    allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(agent_router)
    app.include_router(router)
    app.include_router(applications_router)
    app.include_router(campaigns_router)
    app.include_router(email_imports_router)
    app.include_router(events_router)
    app.include_router(goals_router)
    app.include_router(monitoring_router)
    app.include_router(notifications_router)
    app.include_router(schedules_router)
    app.include_router(todos_router)
    return app


app = create_app()
