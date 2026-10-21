"""Приложение FastAPI с подготовкой базы данных при запуске."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.catalog import CatalogError
from app.database import engine, init_db
from app.routers.api import router as api_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="Модуль управления каталогом товаров",
    description="Учебный проект курсовой работы МФЮА.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.exception_handler(CatalogError)
async def handle_catalog_error(_request: Request, error: CatalogError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"detail": error.detail})


@app.get("/", summary="Информация о приложении")
def read_root() -> dict[str, str]:
    return {"message": "Модуль управления каталогом товаров"}


@app.get("/health", summary="Проверка ответа сервера")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
