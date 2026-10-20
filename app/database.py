"""Подключение к SQLite и создание таблиц без удаления существующих данных."""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "catalog.db"


class Base(DeclarativeBase):
    """Общий реестр моделей SQLAlchemy."""


def create_sqlite_engine(database_path: Path) -> Engine:
    """Создать подключение к указанному файлу; тесты передают свой путь."""
    db_engine = create_engine(
        URL.create("sqlite", database=str(database_path.resolve())),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(db_engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    return db_engine


engine = create_sqlite_engine(DATABASE_PATH)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Iterator[Session]:
    """Выдать сеанс на запрос; изменения фиксируются явно через commit()."""
    with SessionLocal() as session:
        yield session


def init_db(db_engine: Engine = engine) -> None:
    """Создать только отсутствующие таблицы; это не механизм миграций."""
    from app.models import Category, Product

    database_file = db_engine.url.database
    if database_file and database_file != ":memory:":
        Path(database_file).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(
        bind=db_engine,
        tables=[Category.__table__, Product.__table__],
    )
