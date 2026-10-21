"""Приложение FastAPI с подготовкой базы данных при запуске."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exception_handlers import request_validation_exception_handler

from app.catalog import CatalogError
from app.database import engine, init_db
from app.routers.api import router as api_router
from app.routers.pages import router as pages_router
from app.web import APP_DIRECTORY, render


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
app.include_router(pages_router)
app.mount("/static", StaticFiles(directory=APP_DIRECTORY / "static"), name="static")


@app.exception_handler(CatalogError)
async def handle_catalog_error(request: Request, error: CatalogError) -> JSONResponse | HTMLResponse:
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail})
    return render(request, "error.html", status_code=error.status_code, status=error.status_code, detail=error.detail)


@app.exception_handler(RequestValidationError)
async def handle_request_validation(request: Request, error: RequestValidationError):
    if request.url.path.startswith("/api/"):
        return await request_validation_exception_handler(request, error)
    return render(request, "error.html", status_code=422, status=422, detail="Неверный адрес или параметры запроса")


@app.get("/", include_in_schema=False)
def read_root() -> RedirectResponse:
    return RedirectResponse("/products", status_code=307)


@app.get("/health", summary="Проверка ответа сервера")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
