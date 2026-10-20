"""Проверки сохранности данных, ограничений и запуска приложения."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import create_sqlite_engine, init_db
from app.models import Category, Product


def add_product(session: Session) -> Product:
    product = Product(
        name=" Ручка синяя ",
        sku=" pen-001 ",
        category=Category(name=" Письменные принадлежности "),
        price_kopecks=4990,
        quantity=20,
    )
    session.add(product)
    session.commit()
    return product


def test_foreign_keys_enabled_for_each_connection(db_engine):
    with db_engine.connect() as first, db_engine.connect() as second:
        assert first.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert second.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1


def test_reinitialization_preserves_data_in_another_process(db_engine, db_session):
    product = add_product(db_session)
    product_id = product.id
    init_db(db_engine)
    assert db_session.scalar(select(func.count()).select_from(Product)) == 1

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json, sqlite3, sys; "
            "connection = sqlite3.connect(sys.argv[1]); "
            "row = connection.execute("
            "'SELECT name, sku, price_kopecks, quantity FROM products WHERE id = ?', "
            "(int(sys.argv[2]),)).fetchone(); "
            "print(json.dumps(row)); connection.close()",
            db_engine.url.database,
            str(product_id),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert json.loads(result.stdout) == ["Ручка синяя", "PEN-001", 4990, 20]


def test_category_names_are_unique_without_case(db_session):
    db_session.add(Category(name="Бумага"))
    db_session.commit()
    db_session.add(Category(name=" БУМАГА "))
    with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
        db_session.commit()
    db_session.rollback()
    db_session.add(Category(name="Тетради"))
    db_session.commit()
    assert db_session.scalar(select(func.count()).select_from(Category)) == 2


def test_product_skus_are_unique_without_case(db_session):
    first = add_product(db_session)
    db_session.add(
        Product(
            name="Другой товар",
            sku="PEN-001",
            category_id=first.category_id,
            price_kopecks=0,
            quantity=0,
        )
    )
    with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(Product)) == 1


def test_product_requires_existing_category(db_session):
    db_session.add(
        Product(
            name="Товар",
            sku="TEST-001",
            category_id=999,
            price_kopecks=100,
            quantity=1,
        )
    )
    with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(Product)) == 0


@pytest.mark.parametrize("load_products", [False, True])
def test_deleting_nonempty_category_keeps_products(db_session, load_products):
    product = add_product(db_session)
    category_id = product.category_id
    product_id = product.id
    db_session.expunge_all()
    category = db_session.get(Category, category_id)
    if load_products:
        assert len(category.products) == 1
    db_session.delete(category)
    with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(Category, category_id) is not None
    assert db_session.get(Product, product_id) is not None


def test_empty_category_can_be_deleted(db_session):
    category = Category(name="Пустая категория")
    db_session.add(category)
    db_session.commit()
    category_id = category.id
    db_session.delete(category)
    db_session.commit()
    assert db_session.get(Category, category_id) is None


@pytest.mark.parametrize("field", ["price_kopecks", "quantity"])
@pytest.mark.parametrize("value", [-1, 1.5])
def test_database_itself_rejects_invalid_numbers(db_engine, db_session, field, value):
    product = add_product(db_session)
    values = {
        "name": "Товар",
        "name_normalized": "товар",
        "sku": "RAW-001",
        "category_id": product.category_id,
        "price_kopecks": 100,
        "quantity": 1,
        field: value,
    }
    constraint = "ck_product_price" if field == "price_kopecks" else "ck_product_quantity"
    # Core INSERT обходит проверки присваивания ORM: проверяем именно SQLite.
    with pytest.raises(IntegrityError, match=constraint):
        with db_engine.begin() as connection:
            connection.execute(insert(Product.__table__).values(**values))


@pytest.mark.parametrize("field", ["price_kopecks", "quantity"])
@pytest.mark.parametrize("value", [True, 1.5, -1, 2**63])
def test_model_rejects_boolean_fraction_negative_and_overflow(field, value):
    product = Product()
    with pytest.raises(ValueError):
        setattr(product, field, value)


@pytest.mark.parametrize("field", ["category_id", "price_kopecks", "quantity"])
def test_database_requires_mandatory_fields(db_engine, db_session, field):
    product = add_product(db_session)
    values = {
        "name": "Товар",
        "name_normalized": "товар",
        "sku": "RAW-001",
        "category_id": product.category_id,
        "price_kopecks": 100,
        "quantity": 1,
        field: None,
    }
    with pytest.raises(IntegrityError, match="NOT NULL constraint failed"):
        with db_engine.begin() as connection:
            connection.execute(insert(Product.__table__).values(**values))


@pytest.mark.parametrize("sku", ["", "РУЧКА-001", "PEN 001", "ß", "A" * 65])
def test_invalid_sku_is_rejected(sku):
    with pytest.raises(ValueError):
        Product(sku=sku)


def test_database_rejects_noncanonical_sku(db_engine, db_session):
    product = add_product(db_session)
    with pytest.raises(IntegrityError, match="ck_product_sku"):
        with db_engine.begin() as connection:
            connection.execute(
                insert(Product.__table__).values(
                    name="Товар",
                    name_normalized="товар",
                    sku="lowercase-001",
                    category_id=product.category_id,
                    price_kopecks=100,
                    quantity=1,
                )
            )


@pytest.mark.parametrize("model", [Category, Product])
def test_blank_name_is_rejected(model):
    with pytest.raises(ValueError):
        model(name=" \t\n ")


def test_names_update_with_their_search_representation(db_session):
    product = add_product(db_session)
    category = product.category
    product.name = " ТЕТРАДЬ "
    category.name = " БУМАГА "
    db_session.commit()
    db_session.expire_all()
    assert product.name == "ТЕТРАДЬ"
    assert product.name_normalized == "тетрадь"
    assert category.name == "БУМАГА"
    assert category.name_normalized == "бумага"


def test_timestamps_are_assigned_and_updated(db_session):
    product = add_product(db_session)
    created_at = product.created_at
    assert isinstance(created_at, datetime)
    assert isinstance(product.updated_at, datetime)
    old = datetime(2000, 1, 1)
    product.updated_at = old
    db_session.commit()
    product.quantity = 19
    db_session.commit()
    db_session.refresh(product)
    assert product.created_at == created_at
    assert product.updated_at > old
    assert product.updated_at.tzinfo is None  # Установленный контракт хранения UTC.


def test_database_path_survives_working_directory_change(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = create_sqlite_engine(Path("storage/catalog.db"))
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.chdir(other)
    try:
        init_db(engine)
        assert (tmp_path / "storage/catalog.db").is_file()
        assert not (other / "storage/catalog.db").exists()
    finally:
        engine.dispose()


def test_app_initializes_database_and_preserves_it_on_restart(tmp_path, monkeypatch):
    import app.main as main

    engine = create_sqlite_engine(tmp_path / "app/catalog.db")
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "init_db", lambda: init_db(engine))
    try:
        with TestClient(main.app) as client:
            assert client.get("/health").json() == {"status": "ok"}
            assert set(inspect(engine).get_table_names()) == {"categories", "products"}
            with Session(engine) as session:
                product_id = add_product(session).id
        with TestClient(main.app) as client:
            assert client.get("/").status_code == 200
            with Session(engine) as session:
                assert session.get(Product, product_id).sku == "PEN-001"
    finally:
        engine.dispose()
