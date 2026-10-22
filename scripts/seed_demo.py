"""Заполнение каталога: python -m scripts.seed_demo.

Перед записью в существующую базу сохраняется SQLite backup. Существующие
товары/категории не перезаписываются, совпадения артикулов пропускаются.
"""

import argparse
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.database import DATABASE_PATH, create_sqlite_engine, init_db
from app.demo_data import seed_catalog


def backup_database(database_path: Path) -> Path | None:
    if not database_path.exists():
        return None
    folder = database_path.parent / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = folder / f"catalog-before-demo-{timestamp}-{uuid4().hex[:8]}.db"
    # backup() включает зафиксированные данные WAL в согласованную копию базы.
    try:
        with closing(sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def load_demo(database_path: Path) -> dict:
    database_path = database_path.resolve()
    backup_path = backup_database(database_path)  # При ошибке копирования запись не начинается.
    engine = create_sqlite_engine(database_path)
    try:
        init_db(engine)
        result = seed_catalog(engine)
    finally:
        engine.dispose()
    return {"database": str(database_path), "backup": str(backup_path) if backup_path else None,
            **asdict(result)}


def main():
    parser = argparse.ArgumentParser(description="Добавить 1200 демонстрационных товаров без перезаписи данных")
    parser.add_argument("--database", type=Path, default=DATABASE_PATH,
                        help="Путь SQLite; по умолчанию data/catalog.db проекта")
    arguments = parser.parse_args()
    result = load_demo(arguments.database)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
