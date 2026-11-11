"""HTML-сценарии проверяются с теми же временными БД, что и API."""

from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import pytest


class Inputs(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.values = {}
        self.next_url = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input":
            self.values[attrs.get("name")] = attrs.get("value")
        if tag == "a" and attrs.get("rel") == "next":
            self.next_url = attrs["href"]


class CatalogView(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.pages = {}
        self.current = None
        self.disabled = 0
        self.metrics = {}
        self.metric = None
        self.read_value = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "page-number" in attrs.get("class", "").split():
            number = int(attrs["aria-label"].split()[-1])
            self.pages[number] = attrs.get("href")
            if attrs.get("aria-current") == "page":
                self.current = number
        if attrs.get("class") == "page-step" and attrs.get("aria-disabled") == "true":
            self.disabled += 1
        if "data-metric" in attrs:
            self.metric = attrs["data-metric"]
        if tag == "dd" and self.metric:
            self.metrics[self.metric] = {"value": int(attrs["data-value"]), "text": ""}
            self.read_value = True

    def handle_data(self, data):
        if self.read_value:
            self.metrics[self.metric]["text"] += data

    def handle_endtag(self, tag):
        if tag == "dd":
            self.read_value = False
            self.metric = None


def new_category(client, name="Письменные принадлежности"):
    response = client.post("/categories", data={"name": name, "description": "Для письма"}, follow_redirects=False)
    assert response.status_code == 303
    return next(item["id"] for item in client.get("/api/categories").json() if item["name"] == name)


def fields(default_category_id, **changes):
    return {"name": "Ручка синяя", "sku": "pen-001", "description": "Удобный корпус",
            "category_id": str(default_category_id), "price": "49,90", "quantity": "20", **changes}


def add_product(client, category_id, **changes):
    response = client.post("/products", data=fields(category_id, **changes), follow_redirects=False)
    assert response.status_code == 303, response.text
    return response.headers["location"].split("?")[0]


def test_empty_catalog_root_assets_and_no_category(api_client):
    root = api_client.get("/", follow_redirects=False)
    assert root.status_code == 307 and root.headers["location"] == "/products"
    assert "Создать категорию" in api_client.get("/").text
    assert "Пока нет категорий" in api_client.get("/categories").text
    form = api_client.get("/products/new")
    assert "Сначала создайте категорию" in form.text and "disabled" in form.text
    for path, mime in [("styles.css", "text/css"), ("app.js", "javascript")]:
        response = api_client.get("/static/" + path)
        assert response.status_code == 200 and mime in response.headers["content-type"]


def test_html_product_crud_is_visible_in_api(api_client):
    cat = new_category(api_client)
    path = add_product(api_client, cat)
    detail = api_client.get(path + "?saved=created")
    assert detail.status_code == 200 and "Товар добавлен" in detail.text
    assert "49,90" in detail.text and "PEN-001" in detail.text
    stored = api_client.get("/api" + path).json()
    assert stored["price"] == "49.90" and stored["quantity"] == 20
    form = Inputs(api_client.get(path + "/edit").text)
    assert form.values["price"] == "49.90" and form.values["sku"] == "PEN-001"
    update = api_client.post(path + "/edit", data=fields(cat, name="Ручка чёрная", quantity="0", price="0"), follow_redirects=False)
    assert update.status_code == 303 and update.headers["location"] == path + "?saved=updated"
    assert api_client.get("/api" + path).json()["quantity"] == 0
    assert "Ручка чёрная" in api_client.get("/products").text
    assert api_client.get(path + "/delete").status_code == 200
    assert api_client.get("/api" + path).status_code == 200  # GET подтверждения не удаляет.
    removed = api_client.post(path + "/delete", follow_redirects=False)
    assert removed.status_code == 303
    assert api_client.get("/api" + path).status_code == 404
    assert "Товар удалён" in api_client.get(removed.headers["location"]).text


def test_category_rename_count_protection_and_delete(api_client):
    cat = new_category(api_client)
    path = add_product(api_client, cat)
    category_path = f"/categories/{cat}"
    response = api_client.post(category_path + "/edit", data={"name": "Канцелярия", "description": "Обновлено"})
    assert response.status_code == 200 and "Изменения сохранены" in response.text
    assert api_client.get("/api" + path).json()["category_name"] == "Канцелярия"
    assert f'/products?category_id={cat}">1</a>' in api_client.get("/categories").text
    confirmation = api_client.get(category_path + "/delete")
    assert "Категория используется" in confirmation.text and '<form method="post"' not in confirmation.text
    rejected = api_client.post(category_path + "/delete")
    assert rejected.status_code == 409 and "Нельзя удалить категорию с товарами" in rejected.text
    assert api_client.get("/api" + path).status_code == 200
    api_client.post(path + "/delete")
    assert "Удалить категорию?" in api_client.get(category_path + "/delete").text
    assert api_client.post(category_path + "/delete", follow_redirects=False).status_code == 303
    assert api_client.get(f"/api/categories/{cat}").status_code == 404


@pytest.mark.parametrize("change", [
    {"name": " "}, {"sku": "РУЧКА"}, {"price": "-1"}, {"price": "1.234"},
    {"price": "NaN"}, {"quantity": "1.5"}, {"quantity": "-1"}, {"quantity": "1e2"},
    {"quantity": "9223372036854775808"}, {"category_id": "1.5"}, {"category_id": ""},
    {"description": "A" * 2001}, {"admin": "true"},
])
def test_invalid_form_retains_values_without_insert(api_client, change):
    cat = new_category(api_client)
    data = fields(cat, **change)
    response = api_client.post("/products", data=data)
    assert response.status_code == 422
    assert "Проверьте введённые данные" in response.text
    assert Inputs(response.text).values["name"] == data["name"]
    assert api_client.get("/api/products").json()["total"] == 0


def test_conflict_retains_input_and_previous_product(api_client):
    cat = new_category(api_client)
    first = add_product(api_client, cat)
    second = add_product(api_client, cat, sku="PEN-002")
    response = api_client.post(second + "/edit", data=fields(cat, name="Не сохранено", price="999"))
    assert response.status_code == 409
    assert Inputs(response.text).values["name"] == "Не сохранено"
    assert api_client.get("/api" + second).json()["sku"] == "PEN-002"
    assert api_client.get("/api" + first).json()["price"] == "49.90"


def test_category_duplicate_and_invalid_input_keep_form(api_client):
    new_category(api_client, "Бумага")
    duplicate = api_client.post("/categories", data={"name": "БУМАГА", "description": "Текст"})
    assert duplicate.status_code == 409 and Inputs(duplicate.text).values["name"] == "БУМАГА"
    invalid = api_client.post("/categories", data={"name": " "})
    assert invalid.status_code == 422 and "заполните обязательное поле" in invalid.text


def test_filters_and_pagination_preserve_combination(api_client):
    cat = new_category(api_client)
    for index in range(12):
        add_product(api_client, cat, name=f"Ручка {index:02}", sku=f"PEN-{index}", price="50")
    add_product(api_client, cat, sku="OUT", name="Ручка закончилась", quantity="0")
    query = {"q": "РУЧКА", "category_id": str(cat), "min_price": "50", "max_price": "50", "in_stock": "true", "sort": "name_desc"}
    first = api_client.get("/products", params=query)
    assert first.status_code == 200 and "Найдено: 12" in first.text
    assert first.text.index('class="product-name" href="/products/12"') < first.text.index('class="product-name" href="/products/11"')
    next_url = Inputs(first.text).next_url
    assert CatalogView(first.text).pages[2] == next_url
    next_query = parse_qs(urlparse(next_url).query)
    assert next_query == {**{key: [value] for key, value in query.items()}, "page": ["2"]}
    second = api_client.get(next_url)
    assert "Страница 2 из 2" in second.text and second.text.count('class="product-name"') == 2
    assert Inputs(second.text).next_url is None
    assert "Ручка закончилась" not in first.text + second.text
    assert parse_qs(urlparse(CatalogView(second.text).pages[1]).query) == {
        **{key: [value] for key, value in query.items()}, "page": ["1"]
    }


@pytest.mark.parametrize("query", [{"min_price": "100", "max_price": "1"}, {"sort": "bad"}, {"page": "0"}, {"q": "x" * 201}])
def test_invalid_filter_is_html_with_retained_search(api_client, query):
    response = api_client.get("/products", params={"q": "Ручка", **query})
    assert response.status_code == 422 and "text/html" in response.headers["content-type"]
    assert Inputs(response.text).values["q"] == query.get("q", "Ручка")


def test_user_html_is_escaped_in_views_and_validation(api_client):
    cat = new_category(api_client, '<img src=x onerror="alert(1)">')
    path = add_product(api_client, cat, name='<script>alert("x")</script>', description="<b>Текст</b>")
    for target in ["/products", path, path + "/edit", path + "/delete", "/categories"]:
        response = api_client.get(target)
        assert "<script>alert" not in response.text and '<img src=x' not in response.text
        assert "&lt;" in response.text
    response = api_client.post("/products", data=fields(cat, name='<script>alert("x")</script>', price="bad"))
    assert "<script>alert" not in response.text
    assert Inputs(response.text).values["name"] == '<script>alert("x")</script>'


@pytest.mark.parametrize("path", ["/products/999", "/products/999/edit", "/categories/999/delete", "/products/not-a-number", "/products/9223372036854775808", "/categories/9223372036854775808/edit", "/products/0"])
def test_missing_or_invalid_html_address_keeps_api_error_format(api_client, path):
    response = api_client.get(path)
    assert response.status_code in {404, 422} and "text/html" in response.headers["content-type"]
    api_error = api_client.get("/api/products/999")
    assert api_error.status_code == 404 and api_error.json() == {"detail": "Товар не найден"}


@pytest.mark.parametrize("page, numbers", [
    (1, [1, 2, 3, 4, 5, 120]),
    (2, [1, 2, 3, 4, 5, 120]),
    (60, [1, 58, 59, 60, 61, 62, 120]),
    (119, [1, 116, 117, 118, 119, 120]),
    (120, [1, 116, 117, 118, 119, 120]),
])
def test_numbered_pages_cover_start_middle_and_end(api_client, db_engine, page, numbers):
    from app.demo_data import seed_catalog

    seed_catalog(db_engine)
    response = api_client.get("/products", params={"page": page})
    view = CatalogView(response.text)
    assert response.status_code == 200 and f"Страница {page} из 120" in response.text
    assert sorted(view.pages) == numbers and view.current == page
    assert view.disabled == (1 if page in {1, 120} else 0)
    for number, url in view.pages.items():
        if number != page:
            assert parse_qs(urlparse(url).query)["page"] == [str(number)]


def test_empty_catalog_and_invalid_filters_have_clear_totals(api_client):
    response = api_client.get("/products")
    view = CatalogView(response.text)
    assert view.current == 1 and view.disabled == 2
    assert all(metric["value"] == 0 for metric in view.metrics.values())
    assert view.metrics["value_kopecks"]["text"] == "0,00 ₽"
    invalid = api_client.get("/products", params={"min_price": "100", "max_price": "1"})
    assert invalid.status_code == 422 and not CatalogView(invalid.text).metrics


def test_page_after_last_can_return_to_the_last_existing_page(api_client):
    cat = new_category(api_client)
    add_product(api_client, cat)
    response = api_client.get("/products", params={"page": "999"})
    view = CatalogView(response.text)
    assert response.status_code == 200 and "Страница 999 пуста" in response.text
    assert view.current is None and list(view.pages) == [1]
    assert parse_qs(urlparse(view.pages[1]).query)["page"] == ["1"]
    assert "Показано 0 из 1" in response.text


@pytest.mark.parametrize("query, expected", [
    ({}, (3, 1, 27, 137800)),
    ({"q": "РУЧКА", "min_price": "49.90", "max_price": "100", "in_stock": "true"}, (2, 0, 23, 129800)),
    ({"max_price": "20"}, (1, 0, 4, 8000)),
    ({"category_id": "paper"}, (1, 0, 4, 8000)),
    ({"q": "Нет такого товара"}, (0, 0, 0, 0)),
])
def test_catalog_metrics_follow_the_same_filters_as_products(api_client, query, expected):
    pens = new_category(api_client, "Ручки")
    paper = new_category(api_client, "Бумага")
    add_product(api_client, pens, name="Ручка синяя", sku="BLUE", price="49.90", quantity="20")
    add_product(api_client, pens, name="Ручка гелевая", sku="GEL", price="100", quantity="3")
    add_product(api_client, pens, name="Ручка красная", sku="RED", price="99", quantity="0")
    add_product(api_client, paper, name="Тетрадь", sku="PAPER", price="20", quantity="4")
    if query.get("in_stock"):
        query = {**query, "category_id": str(pens)}
    if query.get("category_id") == "paper":
        query = {**query, "category_id": str(paper)}
    response = api_client.get("/products", params=query)
    view = CatalogView(response.text)
    assert response.status_code == 200
    assert tuple(view.metrics[key]["value"] for key in ["in_stock", "out_of_stock", "units", "value_kopecks"]) == expected
    assert "По выбранным фильтрам, все страницы" in response.text


def test_metrics_include_items_from_other_pages(api_client):
    cat = new_category(api_client)
    for index in range(12):
        add_product(api_client, cat, sku=f"ITEM-{index}", price="1.10", quantity="2")
    for page in [1, 2]:
        response = api_client.get("/products", params={"page": page})
        view = CatalogView(response.text)
        assert view.metrics["in_stock"]["value"] == 12
        assert view.metrics["units"]["value"] == 24
        assert view.metrics["value_kopecks"] == {"value": 2640, "text": "26,40 ₽"}
    assert "Показано 11–12 из 12" in unescape(response.text)


def test_metrics_keep_integer_precision_beyond_sqlite_sum_limit(api_client, db_engine):
    from sqlalchemy.orm import Session
    from app.models import Category, Product, SQLITE_MAX_INTEGER

    with Session(db_engine) as session:
        category = Category(name="Большие значения")
        for sku in ["MAX-1", "MAX-2"]:
            session.add(Product(name=sku, sku=sku, category=category, price_kopecks=SQLITE_MAX_INTEGER, quantity=SQLITE_MAX_INTEGER))
        session.commit()
    response = api_client.get("/products")
    assert response.status_code == 200
    metrics = CatalogView(response.text).metrics
    assert metrics["units"]["value"] == 2 * SQLITE_MAX_INTEGER
    assert metrics["value_kopecks"]["value"] == 2 * SQLITE_MAX_INTEGER ** 2
    assert metrics["value_kopecks"]["text"].endswith(",98 ₽")
