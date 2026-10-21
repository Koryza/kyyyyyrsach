"""Проверка запущенного приложения только чтением: HTTP, схема API и SQLite.

Из корня проекта: .venv/bin/python -m scripts.check_ready
Сервер должен работать на 127.0.0.1:8000 с обычной рабочей базой.
"""

import json
from urllib.error import HTTPError
from urllib.request import urlopen

from sqlalchemy import inspect

from app.database import DATABASE_PATH, engine


def check():
    base = "http://127.0.0.1:8000"
    for path, fragment in [
        ("/", "Поиск по названию"), ("/products", "Ассортимент"),
        ("/categories", "Структура каталога"), ("/products/new", "Новый товар"),
        ("/categories/new", "Новая категория"), ("/docs", "swagger-ui"),
    ]:
        with urlopen(base + path, timeout=5) as response:
            assert response.status == 200
            assert "text/html" in response.headers["Content-Type"]
            assert fragment in response.read().decode()
            if path == "/":
                assert response.url == base + "/products"
        print(path, "200 HTML")
    for path in ["/static/styles.css", "/static/app.js"]:
        with urlopen(base + path, timeout=5) as response:
            assert response.status == 200 and response.read()
        print(path, "200")
    with urlopen(base + "/health", timeout=5) as response:
        assert json.load(response) == {"status": "ok"}
    with urlopen(base + "/api/products", timeout=5) as response:
        listing = json.load(response)
        assert listing["page"] == 1 and listing["page_size"] == 10
        assert isinstance(listing["items"], list) and listing["total"] >= len(listing["items"])
    with urlopen(base + "/api/categories", timeout=5) as response:
        assert isinstance(json.load(response), list)
    with urlopen(base + "/openapi.json", timeout=5) as response:
        schema = json.load(response)
    assert "get" in schema["paths"]["/health"]
    for path, methods in {
        "/api/products": {"get", "post"},
        "/api/products/{product_id}": {"get", "put", "delete"},
        "/api/categories": {"get", "post"},
        "/api/categories/{category_id}": {"get", "put", "delete"},
    }.items():
        assert methods <= schema["paths"][path].keys()
    print("Health, API lists and ten documented operations: OK")
    try:
        urlopen(base + "/missing-page", timeout=5)
    except HTTPError as error:
        assert error.code == 404
    else:
        raise AssertionError("Missing page must return 404")
    assert DATABASE_PATH.is_file(), "Database must already exist after startup"
    try:
        inspector = inspect(engine)
        assert {"categories", "products"} <= set(inspector.get_table_names())
        assert {"category_id", "price_kopecks", "quantity"} <= {
            column["name"] for column in inspector.get_columns("products")
        }
        assert any(
            key["constrained_columns"] == ["category_id"]
            and key["referred_table"] == "categories"
            and key["options"].get("ondelete") == "RESTRICT"
            for key in inspector.get_foreign_keys("products")
        )
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    finally:
        engine.dispose()
    print("SQLite file, schema and foreign keys: OK; no data changed")


if __name__ == "__main__":
    check()
