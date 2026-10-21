"""Каждый тест получает свою файловую SQLite-базу во временной папке."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.database import create_sqlite_engine, init_db


@pytest.fixture
def db_engine(tmp_path) -> Iterator[Engine]:
    engine = create_sqlite_engine(tmp_path / "catalog.db")
    init_db(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Iterator[Session]:
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def api_client(db_engine, monkeypatch):
    from fastapi.testclient import TestClient

    import app.main as main
    from app.database import get_db

    def test_session():
        with Session(db_engine) as session:
            yield session

    monkeypatch.setattr(main, "engine", db_engine)
    monkeypatch.setattr(main, "init_db", lambda: init_db(db_engine))
    monkeypatch.setattr(
        main.app, "dependency_overrides",
        {**main.app.dependency_overrides, get_db: test_session},
    )
    with TestClient(main.app) as client:
        yield client
