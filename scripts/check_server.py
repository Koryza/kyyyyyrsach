"""Изолированный сервер браузерной проверки; рабочую базу не открывает.

Из корня: .venv/bin/python -m scripts.check_server
После остановки временная база автоматически удаляется. Только 127.0.0.1:8001.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy.orm import Session
import uvicorn

import app.main as main
from app.database import create_sqlite_engine, get_db, init_db


def serve():
    with TemporaryDirectory(prefix="catalog-browser-") as folder:
        test_engine = create_sqlite_engine(Path(folder) / "catalog.db")
        main.engine = test_engine
        main.init_db = lambda: init_db(test_engine)

        def test_session():
            with Session(test_engine) as session:
                yield session

        main.app.dependency_overrides[get_db] = test_session

        @main.app.get("/__test_environment", include_in_schema=False)
        def test_environment():
            return {"temporary_database": True}

        uvicorn.run(main.app, host="127.0.0.1", port=8001, log_level="warning")


if __name__ == "__main__":
    serve()
