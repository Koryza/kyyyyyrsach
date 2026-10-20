"""Начальное приложение FastAPI для третьего этапа проекта."""

from fastapi import FastAPI

app = FastAPI(
    title="Модуль управления каталогом товаров",
    description="Учебный проект курсовой работы МФЮА.",
    version="0.1.0",
)


@app.get("/", summary="Информация о приложении")
def read_root() -> dict[str, str]:
    return {"message": "Модуль управления каталогом товаров"}


@app.get("/health", summary="Проверка ответа сервера")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
