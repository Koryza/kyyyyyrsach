"""Страницы каталога. GET читает, POST изменяет и перенаправляет (303)."""

import re
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import catalog
from app.database import get_db
from app.models import SQLITE_MAX_INTEGER, Product
from app.schemas import PAGE_SIZE, CategoryWrite, ProductFilters, ProductWrite, format_price
from app.web import render, validation_messages

router = APIRouter(include_in_schema=False)
Database = Annotated[Session, Depends(get_db)]
RecordId = Annotated[int, Path(ge=1, le=SQLITE_MAX_INTEGER)]


async def read_form(request: Request) -> dict[str, str]:
    async with request.form(max_files=0, max_fields=20) as form:
        return {key: value for key, value in form.items() if isinstance(value, str)}


FormValues = Annotated[dict[str, str], Depends(read_form)]


def integer_fields(values: dict[str, str]) -> dict:
    """HTML отправляет строки; строгие JSON-схемы API при этом не меняются."""
    data = dict(values)
    for field in ("category_id", "quantity"):
        value = data.get(field, "").strip()
        if re.fullmatch(r"[0-9]{1,19}", value):
            data[field] = int(value)
    return data


def product_form(request, session, values, *, product=None, errors=None, status=200):
    return render(
        request, "products/form.html", status_code=status, active="products",
        values=values, product=product, categories=catalog.list_categories(session),
        errors=errors or [],
    )


def category_form(request, values, *, category=None, errors=None, status=200):
    return render(
        request, "categories/form.html", status_code=status, active="categories",
        values=values, category=category, errors=errors or [],
    )


@router.get("/products")
def products(request: Request, session: Database):
    values = dict(request.query_params)
    # Текст уведомления выбирается из фиксированного списка по коду параметра.
    deleted = values.pop("deleted", "") == "1"
    categories = catalog.list_categories(session)
    try:
        filters = ProductFilters.model_validate(values)
    except ValidationError as error:
        return render(
            request, "products/list.html", status_code=422, active="products",
            values=values, categories=categories, products=[], total=0, page=1, pages=1,
            previous_url=None, next_url=None, errors=validation_messages(error), deleted=False,
        )
    items, total = catalog.list_products(session, filters)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    def page_url(page):
        return "/products?" + urlencode({**values, "page": page})

    return render(
        request, "products/list.html", active="products", values=filters.model_dump(),
        categories=categories, products=items, total=total, page=filters.page, pages=pages,
        previous_url=page_url(filters.page - 1) if filters.page > 1 else None,
        next_url=page_url(filters.page + 1) if filters.page < pages else None,
        errors=[], deleted=deleted,
    )


@router.get("/products/new")
def new_product(request: Request, session: Database):
    return product_form(request, session, {"quantity": "0"})


@router.post("/products")
def add_product(request: Request, session: Database, values: FormValues):
    try:
        product = catalog.create_product(session, ProductWrite.model_validate(integer_fields(values)))
    except ValidationError as error:
        return product_form(request, session, values, errors=validation_messages(error), status=422)
    except catalog.CatalogError as error:
        return product_form(request, session, values, errors=[error.detail], status=error.status_code)
    return RedirectResponse(f"/products/{product.id}?saved=created", status_code=303)


@router.get("/products/{product_id}")
def product_detail(request: Request, product_id: RecordId, session: Database):
    saved = {"created": "Товар добавлен", "updated": "Изменения сохранены"}.get(
        request.query_params.get("saved")
    )
    return render(
        request, "products/detail.html", active="products",
        product=catalog.get_product(session, product_id), saved=saved,
    )


@router.get("/products/{product_id}/edit")
def edit_product(request: Request, product_id: RecordId, session: Database):
    product = catalog.get_product(session, product_id)
    values = {
        "name": product.name, "sku": product.sku, "description": product.description or "",
        "category_id": str(product.category_id), "price": format_price(product.price_kopecks),
        "quantity": str(product.quantity),
    }
    return product_form(request, session, values, product=product)


@router.post("/products/{product_id}/edit")
def save_product(request: Request, product_id: RecordId, session: Database, values: FormValues):
    product = catalog.get_product(session, product_id)
    try:
        catalog.update_product(session, product_id, ProductWrite.model_validate(integer_fields(values)))
    except ValidationError as error:
        return product_form(request, session, values, product=product, errors=validation_messages(error), status=422)
    except catalog.CatalogError as error:
        return product_form(request, session, values, product=product, errors=[error.detail], status=error.status_code)
    return RedirectResponse(f"/products/{product_id}?saved=updated", status_code=303)


@router.get("/products/{product_id}/delete")
def confirm_product_delete(request: Request, product_id: RecordId, session: Database):
    return render(request, "products/delete.html", active="products", product=catalog.get_product(session, product_id))


@router.post("/products/{product_id}/delete")
def remove_product(product_id: RecordId, session: Database):
    catalog.delete_product(session, product_id)
    return RedirectResponse("/products?deleted=1", status_code=303)


@router.get("/categories")
def categories(request: Request, session: Database):
    counts = dict(session.execute(
        select(Product.category_id, func.count(Product.id)).group_by(Product.category_id)
    ).all())
    saved = {"created": "Категория добавлена", "updated": "Изменения сохранены", "deleted": "Категория удалена"}.get(
        request.query_params.get("saved")
    )
    return render(
        request, "categories/list.html", active="categories", categories=catalog.list_categories(session),
        counts=counts, saved=saved,
    )


@router.get("/categories/new")
def new_category(request: Request):
    return category_form(request, {})


@router.post("/categories")
def add_category(request: Request, session: Database, values: FormValues):
    try:
        catalog.create_category(session, CategoryWrite.model_validate(values))
    except ValidationError as error:
        return category_form(request, values, errors=validation_messages(error), status=422)
    except catalog.CatalogError as error:
        return category_form(request, values, errors=[error.detail], status=error.status_code)
    return RedirectResponse("/categories?saved=created", status_code=303)


@router.get("/categories/{category_id}/edit")
def edit_category(request: Request, category_id: RecordId, session: Database):
    category = catalog.get_category(session, category_id)
    return category_form(request, {"name": category.name, "description": category.description or ""}, category=category)


@router.post("/categories/{category_id}/edit")
def save_category(request: Request, category_id: RecordId, session: Database, values: FormValues):
    category = catalog.get_category(session, category_id)
    try:
        catalog.update_category(session, category_id, CategoryWrite.model_validate(values))
    except ValidationError as error:
        return category_form(request, values, category=category, errors=validation_messages(error), status=422)
    except catalog.CatalogError as error:
        return category_form(request, values, category=category, errors=[error.detail], status=error.status_code)
    return RedirectResponse("/categories?saved=updated", status_code=303)


@router.get("/categories/{category_id}/delete")
def confirm_category_delete(request: Request, category_id: RecordId, session: Database):
    category = catalog.get_category(session, category_id)
    count = session.scalar(select(func.count()).select_from(Product).where(Product.category_id == category_id))
    return render(request, "categories/delete.html", active="categories", category=category, count=count)


@router.post("/categories/{category_id}/delete")
def remove_category(category_id: RecordId, session: Database):
    catalog.delete_category(session, category_id)
    return RedirectResponse("/categories?saved=deleted", status_code=303)
