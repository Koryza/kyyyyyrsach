"""Категории и товары: поля, связи и ограничения целостности."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base

SQLITE_MAX_INTEGER = 2**63 - 1


def normalize_name(value: str) -> str:
    """Единое представление для поиска и уникальности русских названий."""
    return unicodedata.normalize("NFKC", value).strip().casefold()


def _clean_name(value: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError("Название должно быть строкой")
    value = value.strip()
    if not 1 <= len(value) <= max_length:
        raise ValueError(f"Название должно содержать от 1 до {max_length} символов")
    return value


def _clean_description(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Описание должно быть строкой")
    value = value.strip()
    if len(value) > 2000:
        raise ValueError("Описание не должно превышать 2000 символов")
    return value or None


def _check_integer(value: int, label: str) -> int:
    if type(value) is not int or not 0 <= value <= SQLITE_MAX_INTEGER:
        raise ValueError(f"{label}: требуется неотрицательное целое число в пределах SQLite")
    return value


def utc_now() -> datetime:
    # SQLite хранит DateTime без часового пояса; все такие значения здесь — UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 100", name="ck_category_name"),
        CheckConstraint("length(name_normalized) > 0", name="ck_category_normalized_name"),
        CheckConstraint(
            "description IS NULL OR length(description) <= 2000",
            name="ck_category_description",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    name_normalized: Mapped[str] = mapped_column(Text, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    products: Mapped[list[Product]] = relationship(
        back_populates="category", passive_deletes="all"
    )

    @validates("name")
    def validate_name(self, _key: str, value: str) -> str:
        value = _clean_name(value, 100)
        self.name_normalized = normalize_name(value)
        return value

    @validates("description")
    def validate_description(self, _key: str, value: str | None) -> str | None:
        return _clean_description(value)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 200", name="ck_product_name"),
        CheckConstraint("length(name_normalized) > 0", name="ck_product_normalized_name"),
        CheckConstraint(
            "length(sku) BETWEEN 1 AND 64 AND sku NOT GLOB '*[^A-Z0-9_-]*'",
            name="ck_product_sku",
        ),
        CheckConstraint(
            "description IS NULL OR length(description) <= 2000",
            name="ck_product_description",
        ),
        CheckConstraint(
            "typeof(price_kopecks) = 'integer' AND price_kopecks >= 0",
            name="ck_product_price",
        ),
        CheckConstraint(
            "typeof(quantity) = 'integer' AND quantity >= 0",
            name="ck_product_quantity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    name_normalized: Mapped[str] = mapped_column(Text)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    price_kopecks: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
    category: Mapped[Category] = relationship(back_populates="products")

    @validates("name")
    def validate_name(self, _key: str, value: str) -> str:
        value = _clean_name(value, 200)
        self.name_normalized = normalize_name(value)
        return value

    @validates("sku")
    def validate_sku(self, _key: str, value: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value.strip()):
            raise ValueError("Артикул: 1–64 латинских буквы, цифры, дефис или подчеркивание")
        return value.strip().upper()

    @validates("description")
    def validate_description(self, _key: str, value: str | None) -> str | None:
        return _clean_description(value)

    @validates("price_kopecks", "quantity")
    def validate_integer(self, key: str, value: int) -> int:
        label = "Цена в копейках" if key == "price_kopecks" else "Количество"
        return _check_integer(value, label)
