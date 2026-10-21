"""Сценарии API на временной базе: операции, ошибки и отбор товаров."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models import Category, Product


def category(client, name="Письменные принадлежности"):
    response = client.post("/api/categories", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def product_data(default_category_id, **changes):
    return {
        "name": " Ручка синяя ", "sku": " pen-001 ",
        "category_id": default_category_id, "price": "49,90", "quantity": 20,
        **changes,
    }


def product(client, category_id, **changes):
    response = client.post("/api/products", json=product_data(category_id, **changes))
    assert response.status_code == 201, response.text
    return response.json()


def test_category_create_read_update_and_delete(api_client):
    created = category(api_client, " Бумага ")
    assert created["name"] == "Бумага"
    assert created["description"] is None
    assert "name_normalized" not in created
    path = f'/api/categories/{created["id"]}'
    assert api_client.get(path).json() == created
    assert api_client.get("/api/categories").json() == [created]
    changed = api_client.put(path, json={"name": "БУМАГА", "description": "Для печати"})
    assert changed.status_code == 200
    assert changed.json()["description"] == "Для печати"
    removed = api_client.delete(path)
    assert removed.status_code == 204 and removed.content == b""
    assert api_client.get(path).status_code == 404
    assert api_client.delete(path).status_code == 404


def test_product_create_read_update_and_delete(api_client):
    cat = category(api_client)
    created = product(api_client, cat["id"])
    assert created["name"] == "Ручка синяя"
    assert created["sku"] == "PEN-001"
    assert created["price"] == "49.90"
    assert created["category_name"] == cat["name"]
    assert created["created_at"].endswith("Z")
    assert created["updated_at"].endswith("Z")
    assert "price_kopecks" not in created and "name_normalized" not in created
    path = f'/api/products/{created["id"]}'
    assert api_client.get(path).json() == created
    changed = api_client.put(path, json=product_data(cat["id"], price="10", quantity=3))
    assert changed.status_code == 200
    assert changed.json()["price"] == "10.00"
    assert changed.json()["quantity"] == 3
    assert changed.json()["created_at"] == created["created_at"]
    removed = api_client.delete(path)
    assert removed.status_code == 204 and removed.content == b""
    assert api_client.get(path).status_code == 404
    assert api_client.delete(path).status_code == 404
    assert api_client.get("/api/products").json()["total"] == 0


def test_zero_price_and_zero_quantity_are_valid(api_client):
    created = product(api_client, category(api_client)["id"], price="0", quantity=0)
    assert created["price"] == "0.00"
    assert api_client.get("/api/products").json()["total"] == 1
    assert api_client.get("/api/products", params={"in_stock": "true"}).json()["items"] == []


def test_price_at_sqlite_limit_is_exact(api_client):
    created = product(api_client, category(api_client)["id"], price="92233720368547758.07")
    assert created["price"] == "92233720368547758.07"


def test_duplicate_category_and_failed_rename_preserve_records(api_client):
    first = category(api_client, "Бумага")
    second = category(api_client, "Тетради")
    assert api_client.post("/api/categories", json={"name": " БУМАГА "}).status_code == 409
    path = f'/api/categories/{second["id"]}'
    assert api_client.put(path, json={"name": "бумага"}).status_code == 409
    assert api_client.get(path).json()["name"] == "Тетради"
    assert api_client.put(path, json={"name": "Альбомы"}).status_code == 200
    assert api_client.get(f'/api/categories/{first["id"]}').json()["name"] == "Бумага"


def test_duplicate_sku_and_failed_update_preserve_product(api_client):
    cat_id = category(api_client)["id"]
    first = product(api_client, cat_id)
    assert api_client.post("/api/products", json=product_data(cat_id)).status_code == 409
    second = product(api_client, cat_id, sku="PEN-002")
    path = f'/api/products/{second["id"]}'
    result = api_client.put(path, json=product_data(cat_id, name="Не должно сохраниться"))
    assert result.status_code == 409
    assert api_client.get(path).json() == second
    assert api_client.put(path, json=product_data(cat_id, sku="PEN-003")).status_code == 200
    assert api_client.get(f'/api/products/{first["id"]}').json() == first


def test_category_move_and_rename_keep_relationships(api_client):
    first = category(api_client, "Ручки")
    second = category(api_client, "Товары для школы")
    item = product(api_client, first["id"])
    first_path = f'/api/categories/{first["id"]}'
    assert api_client.delete(first_path).status_code == 409
    assert api_client.get(f'/api/products/{item["id"]}').status_code == 200
    response = api_client.put(first_path, json={"name": "Письменные принадлежности"})
    assert response.status_code == 200
    assert api_client.get(f'/api/products/{item["id"]}').json()["category_name"] == response.json()["name"]
    moved = api_client.put(f'/api/products/{item["id"]}', json=product_data(second["id"]))
    assert moved.status_code == 200 and moved.json()["category_id"] == second["id"]
    assert moved.json()["category_name"] == second["name"]
    assert api_client.delete(first_path).status_code == 204


@pytest.mark.parametrize("method,path,body", [
    ("get", "/api/categories/999", None),
    ("put", "/api/categories/999", {"name": "Категория"}),
    ("delete", "/api/categories/999", None),
    ("get", "/api/products/999", None),
    ("put", "/api/products/999", product_data(1)),
    ("delete", "/api/products/999", None),
    ("post", "/api/products", product_data(999)),
    ("get", "/api/products?category_id=999", None),
])
def test_missing_records_return_404(api_client, method, path, body):
    kwargs = {} if body is None else {"json": body}
    response = api_client.request(method, path, **kwargs)
    assert response.status_code == 404, response.text
    assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("changes", [
    {"name": ""}, {"name": " \t "}, {"name": "А" * 201},
    {"sku": ""}, {"sku": "РУЧКА-1"}, {"sku": "PEN 1"}, {"sku": "A" * 65},
    {"price": "-1"}, {"price": "1.001"}, {"price": "NaN"}, {"price": "Infinity"},
    {"price": "1e2"}, {"price": ""}, {"price": 1.2}, {"price": True}, {"price": 0},
    {"price": "92233720368547758.08"},
    {"quantity": -1}, {"quantity": 1.5}, {"quantity": 1.0}, {"quantity": True},
    {"quantity": 2**63}, {"category_id": "1"}, {"category_id": True},
    {"category_id": 0}, {"category_id": -1}, {"category_id": 2**63},
    {"id": 42}, {"price_kopecks": 1}, {"name_normalized": "подмена"},
    {"description": "А" * 2001},
])
def test_invalid_product_body_returns_422_without_writing(api_client, changes):
    cat_id = category(api_client)["id"]
    response = api_client.post("/api/products", json=product_data(cat_id, **changes))
    assert response.status_code == 422, response.text
    assert api_client.get("/api/products").json()["total"] == 0


@pytest.mark.parametrize("body", [
    {"name": ""}, {"name": " "}, {"name": "А" * 101}, {"name": 7},
    {"name": "Категория", "description": "А" * 2001},
    {"name": "Категория", "id": 42},
])
def test_invalid_category_body_returns_422(api_client, body):
    assert api_client.post("/api/categories", json=body).status_code == 422
    assert api_client.get("/api/categories").json() == []


def test_put_requires_full_product_input(api_client):
    item = product(api_client, category(api_client)["id"])
    path = f'/api/products/{item["id"]}'
    assert api_client.put(path, json={"name": "Новое название"}).status_code == 422
    assert api_client.get(path).json() == item


@pytest.fixture
def selection_catalog(api_client):
    pens = category(api_client, "Ручки")["id"]
    paper = category(api_client, "Бумага")["id"]
    records = [
        product(api_client, pens, name="Ручка синяя", sku="BLUE", price="49.90", quantity=20),
        product(api_client, pens, name="РУЧКА красная", sku="RED", price="99.00", quantity=0),
        product(api_client, pens, name="Ручка гелевая", sku="GEL", price="100.00", quantity=3),
        product(api_client, paper, name="Тетрадь", sku="BOOK", price="20.00", quantity=4),
        product(api_client, paper, name="Скидка 100%_точно/а", sku="GIFT", price="0", quantity=0),
    ]
    return {"pens": pens, "paper": paper, "records": records}


@pytest.mark.parametrize("q,expected", [
    ("ручка", {"BLUE", "RED", "GEL"}), (" СИНЯЯ ", {"BLUE"}),
    ("%", {"GIFT"}), ("_", {"GIFT"}), ("/", {"GIFT"}),
    ("' OR 1=1 --", set()),
])
def test_search_is_case_insensitive_and_special_characters_are_literal(api_client, selection_catalog, q, expected):
    response = api_client.get("/api/products", params={"q": q})
    assert response.status_code == 200, response.text
    assert {item["sku"] for item in response.json()["items"]} == expected
    assert response.json()["total"] == len(expected)


def test_combined_filters_and_inclusive_price_bounds(api_client, selection_catalog):
    response = api_client.get("/api/products", params={
        "q": "РУЧКА", "category_id": selection_catalog["pens"],
        "min_price": "49,90", "max_price": "100.00", "in_stock": "true",
        "sort": "price_desc",
    })
    assert response.status_code == 200, response.text
    assert [item["sku"] for item in response.json()["items"]] == ["GEL", "BLUE"]
    equal = api_client.get("/api/products", params={"min_price": "49.90", "max_price": "49.90"})
    assert [item["sku"] for item in equal.json()["items"]] == ["BLUE"]
    zero = api_client.get("/api/products", params={"max_price": "0"})
    assert [item["sku"] for item in zero.json()["items"]] == ["GIFT"]
    lower = api_client.get("/api/products", params={"min_price": "99.00"})
    assert {item["sku"] for item in lower.json()["items"]} == {"RED", "GEL"}


@pytest.mark.parametrize("params", [
    {"min_price": "10", "max_price": "1"}, {"min_price": "-1"},
    {"max_price": "NaN"}, {"min_price": "1.001"}, {"category_id": "0"},
    {"page": "0"}, {"page": "-1"}, {"page": "1.5"}, {"page": str(2**63)},
    {"sort": "price; DROP TABLE products"}, {"in_stock": "perhaps"},
    {"q": "А" * 201}, {"unexpected": "value"},
])
def test_invalid_filters_return_422(api_client, params):
    response = api_client.get("/api/products", params=params)
    assert response.status_code == 422, response.text


def test_empty_optional_filters_are_ignored(api_client):
    response = api_client.get("/api/products", params={"category_id": "", "min_price": " ", "max_price": ""})
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 10}


@pytest.mark.parametrize("sort,expected", [
    ("name_asc", ["C", "A", "B"]), ("name_desc", ["B", "A", "C"]),
    ("price_asc", ["B", "A", "C"]), ("price_desc", ["A", "C", "B"]),
    ("updated_desc", ["B", "C", "A"]),
])
def test_all_sort_orders_have_stable_ties(api_client, db_engine, sort, expected):
    with Session(db_engine) as session:
        cat = Category(name="Категория")
        session.add_all([
            Product(name="Блокнот", sku="A", category=cat, price_kopecks=2000, quantity=1,
                    updated_at=datetime(2025, 1, 1)),
            Product(name="Ручка", sku="B", category=cat, price_kopecks=1000, quantity=1,
                    updated_at=datetime(2025, 1, 3)),
            Product(name="Аркуш", sku="C", category=cat, price_kopecks=2000, quantity=1,
                    updated_at=datetime(2025, 1, 2)),
        ])
        session.commit()
    response = api_client.get("/api/products", params={"sort": sort})
    assert response.status_code == 200
    assert [item["sku"] for item in response.json()["items"]] == expected


def test_pagination_keeps_total_and_stable_order(api_client, db_engine):
    with Session(db_engine) as session:
        cat = Category(name="Ручки")
        session.add_all([
            Product(name="Ручка", sku=f"PEN-{i:03d}", category=cat, price_kopecks=100, quantity=1)
            for i in range(23)
        ])
        session.commit()
        cat_id = cat.id
    collected = []
    for page, count in [(1, 10), (2, 10), (3, 3), (4, 0)]:
        response = api_client.get("/api/products", params={"q": "РУЧКА", "category_id": cat_id, "page": page})
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == page and data["page_size"] == 10 and data["total"] == 23
        assert len(data["items"]) == count
        collected.extend(item["sku"] for item in data["items"])
    assert collected == [f"PEN-{i:03d}" for i in range(23)]


def test_openapi_documents_operations_and_string_prices(api_client):
    schema = api_client.get("/openapi.json").json()
    assert {"get", "post"} <= schema["paths"]["/api/products"].keys()
    assert {"get", "put", "delete"} <= schema["paths"]["/api/products/{product_id}"].keys()
    assert {"get", "post"} <= schema["paths"]["/api/categories"].keys()
    assert {"get", "put", "delete"} <= schema["paths"]["/api/categories/{category_id}"].keys()
    assert schema["components"]["schemas"]["ProductWrite"]["properties"]["price"]["type"] == "string"
    assert schema["components"]["schemas"]["ProductRead"]["properties"]["price"]["type"] == "string"
    fields = {item["name"] for item in schema["paths"]["/api/products"]["get"]["parameters"]}
    assert {"q", "category_id", "min_price", "max_price", "in_stock", "sort", "page"} <= fields
