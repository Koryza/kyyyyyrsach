"""JSON-интерфейс каталога; бизнес-правила находятся в app.catalog."""

from datetime import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app import catalog
from app.database import get_db
from app.models import SQLITE_MAX_INTEGER, Product
from app.schemas import (
    PAGE_SIZE, CategoryRead, CategoryWrite, ProductFilters,
    ProductPage, ProductRead, ProductWrite, format_price,
)

router = APIRouter(prefix="/api")
Database = Annotated[Session, Depends(get_db)]
RecordId = Annotated[int, Path(ge=1, le=SQLITE_MAX_INTEGER)]


def product_response(product: Product) -> ProductRead:
    return ProductRead(
        id=product.id, name=product.name, sku=product.sku,
        description=product.description, category_id=product.category_id,
        category_name=product.category.name, price=format_price(product.price_kopecks),
        quantity=product.quantity,
        created_at=product.created_at.replace(tzinfo=timezone.utc),
        updated_at=product.updated_at.replace(tzinfo=timezone.utc),
    )


@router.get("/categories", tags=["Категории"], summary="Список категорий")
def list_categories(db: Database) -> list[CategoryRead]:
    return [CategoryRead.model_validate(item) for item in catalog.list_categories(db)]


@router.post("/categories", tags=["Категории"], status_code=status.HTTP_201_CREATED,
             summary="Создать категорию")
def create_category(data: CategoryWrite, db: Database) -> CategoryRead:
    return CategoryRead.model_validate(catalog.create_category(db, data))


@router.get("/categories/{category_id}", tags=["Категории"], summary="Получить категорию")
def get_category(category_id: RecordId, db: Database) -> CategoryRead:
    return CategoryRead.model_validate(catalog.get_category(db, category_id))


@router.put("/categories/{category_id}", tags=["Категории"], summary="Изменить категорию")
def update_category(category_id: RecordId, data: CategoryWrite, db: Database) -> CategoryRead:
    return CategoryRead.model_validate(catalog.update_category(db, category_id, data))


@router.delete("/categories/{category_id}", tags=["Категории"], status_code=204,
               response_class=Response, summary="Удалить пустую категорию")
def delete_category(category_id: RecordId, db: Database) -> Response:
    catalog.delete_category(db, category_id)
    return Response(status_code=204)


@router.get("/products", tags=["Товары"], summary="Список, поиск и фильтрация товаров")
def list_products(db: Database, filters: Annotated[ProductFilters, Query()]) -> ProductPage:
    products, total = catalog.list_products(db, filters)
    return ProductPage(
        items=[product_response(product) for product in products],
        total=total, page=filters.page, page_size=PAGE_SIZE,
    )


@router.post("/products", tags=["Товары"], status_code=status.HTTP_201_CREATED,
             summary="Создать товар")
def create_product(data: ProductWrite, db: Database) -> ProductRead:
    return product_response(catalog.create_product(db, data))


@router.get("/products/{product_id}", tags=["Товары"], summary="Получить товар")
def get_product(product_id: RecordId, db: Database) -> ProductRead:
    return product_response(catalog.get_product(db, product_id))


@router.put("/products/{product_id}", tags=["Товары"], summary="Изменить товар целиком")
def update_product(product_id: RecordId, data: ProductWrite, db: Database) -> ProductRead:
    return product_response(catalog.update_product(db, product_id, data))


@router.delete("/products/{product_id}", tags=["Товары"], status_code=204,
               response_class=Response, summary="Удалить товар")
def delete_product(product_id: RecordId, db: Database) -> Response:
    catalog.delete_product(db, product_id)
    return Response(status_code=204)
