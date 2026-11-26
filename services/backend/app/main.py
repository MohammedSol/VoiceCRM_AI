"""FastAPI application entry-point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from voicecrm_contracts import CrmPort

from app.adapters.crm import FakeCrm, UnconfiguredCrm
from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    yield
    await engine.dispose()


def create_app(crm: CrmPort | None = None) -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    if crm is not None:
        application.state.crm = crm
    elif settings.crm_driver == "fake":
        application.state.crm = FakeCrm()
    else:
        application.state.crm = UnconfiguredCrm()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(v1_router)
    return application


app = create_app()
