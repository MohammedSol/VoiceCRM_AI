"""Shared API test fixtures backed by isolated SQLite databases."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.crm import FakeCrm
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app
from app.models import entities as _entities  # noqa: F401


@pytest.fixture
def api_client(tmp_path: Path) -> Iterator[tuple[TestClient, FakeCrm]]:
    database_path = tmp_path / "api-test.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_db_session():
        async with session_factory() as session:
            yield session

    fake_crm = FakeCrm()
    app = create_app(crm=fake_crm)
    app.dependency_overrides[get_db_session] = override_db_session
    with TestClient(app) as client:
        yield client, fake_crm
    asyncio.run(engine.dispose())
