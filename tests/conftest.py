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
