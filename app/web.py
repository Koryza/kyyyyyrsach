"""Общие средства HTML-страниц; пользовательский текст экранирует Jinja2."""

from datetime import timezone
from hashlib import sha256
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.catalog import CatalogSummary
from app.schemas import format_price

APP_DIRECTORY = Path(__file__).resolve().parent
STATIC_DIRECTORY = APP_DIRECTORY / "static"


def asset_url(request: Request, filename: str) -> str:
    """При изменении файла браузер получает новую ссылку вместо кешированной."""
    version = sha256((STATIC_DIRECTORY / filename).read_bytes()).hexdigest()[:12]
    return f"{request.url_for('static', path=filename)}?v={version}"


def group_number(value: int) -> str:
    return f"{value:,}".replace(",", "\u00a0")


def group_rubles(value: int) -> str:
    return f"{group_number(value // 100)},{value % 100:02d}"


def catalog_charts(summary: CatalogSummary) -> dict:
    total = summary.in_stock + summary.out_of_stock
    percentage = round(summary.in_stock * 100 / total, 1) if total else 0
    categories = sorted(summary.by_category.items(), key=lambda item: (-item[1], item[0].casefold()))
    others = 0
    if len(categories) > 6:
        others = len(categories) - 5
        categories = categories[:5] + [(f"Остальные ({others})", sum(value for _, value in categories[5:]))]
    maximum = max((value for _, value in categories), default=0)
    return {
        "total": total,
        "percentage": percentage,
        "percentage_label": f"{percentage:g}".replace(".", ","),
        "categories": [
            {"name": name, "value": value, "width": round(value * 100 / maximum, 2) if maximum else 0}
            for name, value in categories
        ],
        "others": others,
    }


templates = Jinja2Templates(directory=APP_DIRECTORY / "templates")
templates.env.globals["asset_url"] = asset_url
templates.env.globals["rubles"] = lambda amount: format_price(amount).replace(".", ",")
templates.env.globals["group_number"] = group_number
templates.env.globals["group_rubles"] = group_rubles
templates.env.globals["utc_iso"] = lambda value: value.replace(tzinfo=timezone.utc).isoformat()


def render(request: Request, template: str, *, status_code: int = 200, **context):
    return templates.TemplateResponse(
        request=request, name=template, context=context, status_code=status_code,
    )


def validation_messages(error: ValidationError) -> list[str]:
    labels = {
        "name": "Название", "sku": "Артикул", "description": "Описание",
        "category_id": "Категория", "price": "Цена", "quantity": "Остаток",
        "q": "Поиск", "min_price": "Цена от", "max_price": "Цена до",
        "in_stock": "В наличии", "sort": "Сортировка", "page": "Страница",
    }
    messages = []
    for item in error.errors():
        field = str(item["loc"][0]) if item["loc"] else ""
        label = labels.get(field, "Параметр")
        kind = item["type"]
        context = item.get("ctx", {})
        if kind == "value_error":
            detail = str(context["error"])
        elif kind == "string_too_long":
            detail = f"допустимо не более {context['max_length']} символов"
        elif kind in {"string_too_short", "missing"}:
            detail = "заполните обязательное поле"
        elif field == "sku":
            detail = "используйте латинские буквы, цифры, дефис или подчёркивание"
        elif field in {"quantity", "category_id", "page"}:
            detail = "введите целое число в допустимом диапазоне"
        elif kind == "extra_forbidden":
            detail = "неизвестный параметр запроса"
        else:
            detail = "проверьте значение"
        if field and not detail.startswith(f"{label}:"):
            detail = f"{label}: {detail}"
        messages.append(detail)
    return messages
