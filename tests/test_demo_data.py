"""Загрузка большого набора, повторный запуск, сохранение данных и откат."""

import sqlite3

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.demo_data import DEMO_PRODUCT_COUNT, GROUPS, seed_catalog
from app.models import Category, Product
from scripts.seed_demo import backup_database, load_demo


def test_demo_set_is_large_consistent_and_varied(db_engine):
    result = seed_catalog(db_engine)
    assert result.products_added == DEMO_PRODUCT_COUNT == 1200
    assert result.categories_added == len(GROUPS) == 12 and result.products_skipped == 0
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(Product)) == 1200
        assert len(set(session.scalars(select(Product.name)))) == 1200
        assert session.scalar(select(func.count()).select_from(Product).where(Product.quantity == 0)) == 133
        counts = session.execute(select(Product.category_id, func.count()).group_by(Product.category_id)).all()
        assert len(counts) == 12 and all(count == 100 for _, count in counts)
        assert session.scalar(select(func.min(Product.price_kopecks))) == 1900
        assert session.scalar(select(func.max(Product.price_kopecks))) > 30000
        assert all("Демонстрационный товар" in text for text in session.scalars(select(Product.description)))
        assert session.connection().exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_repeated_load_preserves_edits_and_reuses_existing_category(db_engine):
    with Session(db_engine) as session:
        category = Category(name=" ПИСЬМЕННЫЕ ПРИНАДЛЕЖНОСТИ ", description="Описание пользователя")
        user_product = Product(name="Мой товар", sku="USER-001", category=category, price_kopecks=12345, quantity=7)
        session.add(user_product)
        session.commit()
        user_id = user_product.id
        category_id = category.id
    first = seed_catalog(db_engine)
    assert first.categories_added == 11
    with Session(db_engine) as session:
        demo = session.scalar(select(Product).where(Product.sku == "DEMO-01-01-01"))
        demo.name, demo.price_kopecks, demo.quantity = "Изменён пользователем", 123, 0
        session.commit()
        edited_id = demo.id
    second = seed_catalog(db_engine)
    assert second.products_added == second.categories_added == 0 and second.products_skipped == 1200
    with Session(db_engine) as session:
        assert session.get(Category, category_id).description == "Описание пользователя"
        user = session.get(Product, user_id)
        assert (user.name, user.price_kopecks, user.quantity) == ("Мой товар", 12345, 7)
        demo = session.get(Product, edited_id)
        assert (demo.name, demo.price_kopecks, demo.quantity) == ("Изменён пользователем", 123, 0)
        assert session.scalar(select(func.count()).select_from(Product)) == 1201


def test_user_sku_collision_is_skipped_without_overwrite(db_engine):
    with Session(db_engine) as session:
        session.add(Product(name="Собственная запись", sku="DEMO-01-01-01",
                            category=Category(name="Другая категория"), price_kopecks=9, quantity=3))
        session.commit()
    result = seed_catalog(db_engine)
    assert result.products_added == 1199 and result.products_skipped == 1
    with Session(db_engine) as session:
        product = session.scalar(select(Product).where(Product.sku == "DEMO-01-01-01"))
        assert product.name == "Собственная запись" and product.category.name == "Другая категория"


def test_failure_mid_load_rolls_back_all_inserts(db_engine):
    def fail_products(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.startswith("INSERT INTO products"):
            raise RuntimeError("Искусственный сбой записи")
    event.listen(db_engine, "before_cursor_execute", fail_products)
    try:
        with pytest.raises(RuntimeError, match="Искусственный сбой"):
            seed_catalog(db_engine)
    finally:
        event.remove(db_engine, "before_cursor_execute", fail_products)
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(Category)) == 0
        assert session.scalar(select(func.count()).select_from(Product)) == 0


def test_backup_contains_original_rows_and_loader_can_create_new_file(tmp_path):
    database = tmp_path / "catalog.db"
    first = load_demo(database)
    assert first["backup"] is None and first["products_added"] == 1200
    second = load_demo(database)
    assert second["products_added"] == 0 and second["products_skipped"] == 1200
    with sqlite3.connect(second["backup"]) as connection:
        assert connection.execute("SELECT count(*) FROM products").fetchone()[0] == 1200
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_backup_uses_committed_wal_data(tmp_path):
    database = tmp_path / "wal.db"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE note (value TEXT)")
        connection.execute("INSERT INTO note VALUES ('Сохранено в WAL')")
        connection.commit()
        backup = backup_database(database)
        with sqlite3.connect(backup) as copy:
            assert copy.execute("SELECT value FROM note").fetchone()[0] == "Сохранено в WAL"


def test_backup_failure_prevents_loading(tmp_path, monkeypatch):
    import scripts.seed_demo as loader
    database = tmp_path / "catalog.db"
    def fail(_path):
        raise OSError("Нет места для копии")
    monkeypatch.setattr(loader, "backup_database", fail)
    with pytest.raises(OSError, match="Нет места"):
        loader.load_demo(database)
    assert not database.exists()
