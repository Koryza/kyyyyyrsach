"""Общие средства HTML-страниц; пользовательский текст экранирует Jinja2."""

from datetime import timezone
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.schemas import format_price

APP_DIRECTORY = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=APP_DIRECTORY / "templates")
templates.env.globals["rubles"] = lambda amount: format_price(amount).replace(".", ",")
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
