"""Общие операции каталога для API и HTML-страниц."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Category, Product, normalize_name
from app.schemas import PAGE_SIZE, CategoryWrite, ProductFilters, ProductWrite


class CatalogError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _commit(session: Session, foreign_key_message: str = "Связанная категория изменилась. Обновите каталог.") -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        message = str(error.orig)
        if "UNIQUE constraint failed: categories.name_normalized" in message:
            raise CatalogError(409, "Категория с таким названием уже существует") from error
        if "UNIQUE constraint failed: products.sku" in message:
            raise CatalogError(409, "Товар с таким артикулом уже существует") from error
        if "FOREIGN KEY constraint failed" in message:
            raise CatalogError(409, foreign_key_message) from error
        raise


def get_category(session: Session, category_id: int) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise CatalogError(404, "Категория не найдена")
    return category


def list_categories(session: Session) -> list[Category]:
    return list(session.scalars(select(Category).order_by(Category.name_normalized, Category.id)))


def _check_category_name(session: Session, name: str, current_id: int | None = None) -> None:
    query = select(Category.id).where(Category.name_normalized == normalize_name(name))
    if current_id is not None:
        query = query.where(Category.id != current_id)
    if session.scalar(query) is not None:
        raise CatalogError(409, "Категория с таким названием уже существует")


def create_category(session: Session, data: CategoryWrite) -> Category:
    _check_category_name(session, data.name)
    category = Category(name=data.name, description=data.description)
    session.add(category)
    _commit(session)
    session.refresh(category)
    return category


def update_category(session: Session, category_id: int, data: CategoryWrite) -> Category:
    category = get_category(session, category_id)
    _check_category_name(session, data.name, category_id)
    category.name = data.name
    category.description = data.description
    _commit(session)
    session.refresh(category)
    return category


def delete_category(session: Session, category_id: int) -> None:
    category = get_category(session, category_id)
    used = session.scalar(select(Product.id).where(Product.category_id == category_id).limit(1))
    if used is not None:
        raise CatalogError(409, "Нельзя удалить категорию с товарами")
    session.delete(category)
    _commit(session, "Нельзя удалить категорию с товарами")


def get_product(session: Session, product_id: int) -> Product:
    product = session.scalar(
        select(Product).options(joinedload(Product.category)).where(Product.id == product_id)
    )
    if product is None:
        raise CatalogError(404, "Товар не найден")
    return product


def _check_sku(session: Session, sku: str, current_id: int | None = None) -> None:
    query = select(Product.id).where(Product.sku == sku)
    if current_id is not None:
        query = query.where(Product.id != current_id)
    if session.scalar(query) is not None:
        raise CatalogError(409, "Товар с таким артикулом уже существует")


def create_product(session: Session, data: ProductWrite) -> Product:
    category = get_category(session, data.category_id)
    _check_sku(session, data.sku)
    product = Product(
        name=data.name, sku=data.sku, description=data.description,
        category=category, price_kopecks=data.price_kopecks, quantity=data.quantity,
    )
    session.add(product)
    _commit(session)
    session.refresh(product)
    return product


def update_product(session: Session, product_id: int, data: ProductWrite) -> Product:
    product = get_product(session, product_id)
    category = get_category(session, data.category_id)
    _check_sku(session, data.sku, product_id)
    product.name = data.name
    product.sku = data.sku
    product.description = data.description
    product.category = category
    product.price_kopecks = data.price_kopecks
    product.quantity = data.quantity
    _commit(session)
    session.refresh(product)
    return product


def delete_product(session: Session, product_id: int) -> None:
    session.delete(get_product(session, product_id))
    _commit(session)


def list_products(session: Session, filters: ProductFilters) -> tuple[list[Product], int]:
    conditions = []
    if filters.category_id is not None:
        get_category(session, filters.category_id)
        conditions.append(Product.category_id == filters.category_id)
    if filters.q:
        conditions.append(Product.name_normalized.contains(normalize_name(filters.q), autoescape=True))
    if filters.min_price_kopecks is not None:
        conditions.append(Product.price_kopecks >= filters.min_price_kopecks)
    if filters.max_price_kopecks is not None:
        conditions.append(Product.price_kopecks <= filters.max_price_kopecks)
    if filters.in_stock:
        conditions.append(Product.quantity > 0)

    orders = {
        "name_asc": Product.name_normalized.asc(),
        "name_desc": Product.name_normalized.desc(),
        "price_asc": Product.price_kopecks.asc(),
        "price_desc": Product.price_kopecks.desc(),
        "updated_desc": Product.updated_at.desc(),
    }
    total = session.scalar(select(func.count()).select_from(Product).where(*conditions))
    query = (
        select(Product).options(joinedload(Product.category)).where(*conditions)
        .order_by(orders[filters.sort], Product.id.asc())
        .limit(PAGE_SIZE).offset((filters.page - 1) * PAGE_SIZE)
    )
    return list(session.scalars(query)), total
