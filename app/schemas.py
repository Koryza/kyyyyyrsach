"""Входные данные и публичные ответы API каталога."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import SQLITE_MAX_INTEGER

PAGE_SIZE = 10


def price_to_kopecks(value: str) -> int:
    """Разобрать рубли без float, округления и экспоненциальной записи."""
    value = value.strip()
    if len(value) > 32 or not re.fullmatch(r"[0-9]+(?:[.,][0-9]{1,2})?", value):
        raise ValueError("Цена: неотрицательная строка рублей, максимум два знака после разделителя")
    rubles = Decimal(value.replace(",", "."))
    if rubles > Decimal(SQLITE_MAX_INTEGER) / 100:
        raise ValueError("Цена превышает допустимое значение SQLite")
    return int(rubles * 100)


def format_price(kopecks: int) -> str:
    return f"{kopecks // 100}.{kopecks % 100:02d}"


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CategoryWrite(InputModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class ProductWrite(InputModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    description: str | None = Field(default=None, max_length=2000)
    category_id: int = Field(strict=True, ge=1, le=SQLITE_MAX_INTEGER)
    price: str = Field(
        min_length=1, max_length=32,
        description='Цена в рублях строкой, например "49.90" или "49,90".',
    )
    quantity: int = Field(strict=True, ge=0, le=SQLITE_MAX_INTEGER)

    @field_validator("sku")
    @classmethod
    def canonical_sku(cls, value: str) -> str:
        return value.upper()

    @field_validator("price")
    @classmethod
    def canonical_price(cls, value: str) -> str:
        return format_price(price_to_kopecks(value))

    @property
    def price_kopecks(self) -> int:
        return price_to_kopecks(self.price)


class ProductFilters(InputModel):
    q: str = Field(default="", max_length=200)
    category_id: int | None = Field(default=None, ge=1, le=SQLITE_MAX_INTEGER)
    min_price: str | None = Field(default=None, max_length=32)
    max_price: str | None = Field(default=None, max_length=32)
    in_stock: bool = False
    sort: Literal[
        "name_asc", "name_desc", "price_asc", "price_desc", "updated_desc"
    ] = "name_asc"
    page: int = Field(default=1, ge=1, le=SQLITE_MAX_INTEGER // PAGE_SIZE)

    @field_validator("category_id", mode="before")
    @classmethod
    def empty_category(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("min_price", "max_price")
    @classmethod
    def canonical_bound(cls, value: str | None) -> str | None:
        if value is None or not value:
            return None
        return format_price(price_to_kopecks(value))

    @model_validator(mode="after")
    def check_range(self) -> Self:
        if (
            self.min_price_kopecks is not None
            and self.max_price_kopecks is not None
            and self.min_price_kopecks > self.max_price_kopecks
        ):
            raise ValueError("Минимальная цена не может превышать максимальную")
        return self

    @property
    def min_price_kopecks(self) -> int | None:
        return None if self.min_price is None else price_to_kopecks(self.min_price)

    @property
    def max_price_kopecks(self) -> int | None:
        return None if self.max_price is None else price_to_kopecks(self.max_price)


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None


class ProductRead(BaseModel):
    id: int
    name: str
    sku: str
    description: str | None
    category_id: int
    category_name: str
    price: str
    quantity: int
    created_at: datetime
    updated_at: datetime


class ProductPage(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int
