"""Браузерная проверка на отдельном сервере scripts/check_server.py.

Нужен Playwright с Chromium в среде проверки; в зависимости приложения не входит.
Запускать только против тестового сервера. Аргумент --output задаёт папку снимков.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--chromium", default="/usr/bin/chromium")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
base = "http://127.0.0.1:8001"
checks = []
product_cases = []


def passed(name):
    checks.append(name)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=args.chromium, args=["--no-sandbox"])
    browser_version = browser.version
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="ru-RU", timezone_id="Europe/Kirov")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    # Этот специальный маршрут существует только у тестового сервера.
    assert context.request.get(base + "/__test_environment").json() == {"temporary_database": True}
    assert context.request.get(base + "/api/products").json()["total"] == 0, "Тестовая база должна быть пустой"
    page.goto(base)
    expect(page.get_by_role("heading", name="Добавьте первый товар")).to_be_visible()
    passed("Переход с главной страницы и пустой каталог")
    page.get_by_role("link", name="Создать категорию").click()
    page.get_by_label("Название *", exact=True).fill("Письменные принадлежности")
    page.get_by_label("Описание", exact=True).fill("Ручки, карандаши и маркеры")
    page.get_by_role("button", name="Добавить категорию").click()
    expect(page.get_by_role("status")).to_have_text("Категория добавлена")
    passed("Создание категории через форму")
    for name, description in [("Бумага и тетради", "Для учёбы и работы"), ("Организация рабочего места", "Всё на своём месте")]:
        response = context.request.post(base + "/api/categories", data={"name": name, "description": description}, headers={"Content-Type": "application/json"})
        assert response.status == 201
    cats = {item["name"]: item["id"] for item in context.request.get(base + "/api/categories").json()}
    page.get_by_role("link", name="Товары", exact=True).click()
    page.get_by_role("link", name="Добавить товар", exact=True).first.click()
    page.get_by_label("Название *", exact=True).fill("Ручка шариковая синяя")
    page.get_by_label("Артикул *", exact=True).fill("pen-001")
    page.get_by_label("Категория *", exact=True).select_option(str(cats["Письменные принадлежности"]))
    page.get_by_label("Описание", exact=True).fill("Синяя паста, линия 0,7 мм. Удобный корпус для ежедневных записей.")
    page.get_by_label("Цена, ₽ *", exact=True).fill("49,90")
    page.get_by_label("Остаток, шт. *", exact=True).fill("24")
    page.get_by_role("button", name="Добавить товар", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Товар добавлен")
    product_path = page.url.removeprefix(base).split("?")[0]
    expect(page.get_by_text("49,90 ₽", exact=False).first).to_be_visible()
    original = context.request.get(base + "/api" + product_path).json()
    created = {"price": original["price"], "quantity": original["quantity"]}
    assert created == {"price": "49.90", "quantity": 24}
    product_cases.append({
        "id": "create_product",
        "name": "Создание товара",
        "input": {"price": "49,90", "quantity": 24},
        "expected": {"price": "49.90", "quantity": 24},
        "actual": created,
        "passed": True,
    })
    page.screenshot(path=str(args.output / "02-product-detail.png"), full_page=True)
    passed("Создание товара, цена с запятой, карточка и локальное время")
    page.get_by_role("link", name="Редактировать", exact=True).click()
    page.screenshot(path=str(args.output / "03-product-form.png"), full_page=True)
    page.get_by_label("Цена, ₽ *", exact=True).fill("1.234")
    with page.expect_response(lambda response: response.url == base + product_path + "/edit" and response.request.method == "POST") as invalid:
        page.get_by_role("button", name="Сохранить изменения").click()
    expect(page.get_by_role("alert")).to_contain_text("Проверьте введённые данные")
    expect(page.get_by_label("Цена, ₽ *", exact=True)).to_have_value("1.234")
    expect(page.get_by_label("Название *", exact=True)).to_have_value("Ручка шариковая синяя")
    unchanged = context.request.get(base + "/api" + product_path).json()
    assert invalid.value.status == 422 and unchanged == original
    product_cases.append({
        "id": "invalid_price",
        "name": "Цена с тремя знаками после точки",
        "input": {"price": "1.234"},
        "expected": {"http_status": 422, "saved_price": "49.90", "record_unchanged": True},
        "actual": {"http_status": invalid.value.status, "saved_price": unchanged["price"], "record_unchanged": unchanged == original},
        "passed": True,
    })
    page.screenshot(path=str(args.output / "04-validation.png"), full_page=True)
    page.get_by_role("alert").screenshot(path=str(args.output / "10-validation-message.png"))
    passed("Серверная валидация цены с сохранением введённых полей")
    page.get_by_label("Цена, ₽ *", exact=True).fill("54,90")
    page.get_by_label("Остаток, шт. *", exact=True).fill("18")
    page.get_by_role("button", name="Сохранить изменения").click()
    expect(page.get_by_role("status")).to_have_text("Изменения сохранены")
    updated = context.request.get(base + "/api" + product_path).json()
    changed_values = {"price": updated["price"], "quantity": updated["quantity"]}
    assert changed_values == {"price": "54.90", "quantity": 18}
    product_cases.append({
        "id": "update_product",
        "name": "Изменение цены и остатка",
        "input": {"price": "54,90", "quantity": 18},
        "expected": {"price": "54.90", "quantity": 18},
        "actual": changed_values,
        "passed": True,
    })
    page.screenshot(path=str(args.output / "11-product-updated.png"), full_page=True)
    passed("Изменение цены и остатка видно через API")
    assortment = [
        ("Карандаш графитный HB", "PEN-002", "Письменные принадлежности", "29.00", 48),
        ("Маркер текстовый жёлтый", "PEN-003", "Письменные принадлежности", "89.00", 12),
        ("Ручка гелевая чёрная", "PEN-004", "Письменные принадлежности", "79.90", 0),
        ("Ручка шариковая красная", "PEN-005", "Письменные принадлежности", "54.90", 16),
        ("Блокнот на пружине А5", "PAP-001", "Бумага и тетради", "189.00", 15),
        ("Бумага офисная А4, 500 листов", "PAP-002", "Бумага и тетради", "449.00", 8),
        ("Тетрадь в клетку, 48 листов", "PAP-003", "Бумага и тетради", "69.00", 32),
        ("Стикеры для заметок", "PAP-004", "Бумага и тетради", "119.00", 0),
        ("Папка с кольцами А4", "ORG-001", "Организация рабочего места", "249.00", 9),
        ("Подставка для карандашей", "ORG-002", "Организация рабочего места", "299.00", 6),
        ("Набор скрепок, 100 шт.", "ORG-003", "Организация рабочего места", "59.00", 40),
        ("Ластик белый", "PEN-006", "Письменные принадлежности", "35.00", 25),
    ]
    for name, sku, category, price, quantity in assortment:
        response = context.request.post(base + "/api/products", data={"name": name, "sku": sku, "category_id": cats[category], "price": price, "quantity": quantity}, headers={"Content-Type": "application/json"})
        assert response.status == 201, response.text()
    page.goto(base + "/products")
    expect(page.get_by_text("Найдено: 13")).to_be_visible()
    page.screenshot(path=str(args.output / "01-products-desktop.png"), full_page=True)
    expect(page.locator("tbody tr")).to_have_count(10)
    page.get_by_role("link", name="Далее").click()
    expect(page.locator("tbody tr")).to_have_count(3)
    page.get_by_role("link", name="Назад").click()
    passed("Пагинация 10 + 3 товара и переход назад")
    page.get_by_label("Поиск по названию").fill("РУЧКА")
    page.get_by_label("Категория", exact=True).select_option(str(cats["Письменные принадлежности"]))
    page.get_by_label("Цена от, ₽").fill("50")
    page.get_by_label("Цена до, ₽").fill("80")
    page.get_by_label("Только в наличии").check()
    page.get_by_label("Сортировка").select_option("price_desc")
    page.get_by_role("button", name="Применить").click()
    expect(page.locator("tbody tr")).to_have_count(2)
    expect(page.get_by_text("Ручка гелевая чёрная", exact=True)).to_have_count(0)
    page.screenshot(path=str(args.output / "05-combined-filters.png"), full_page=True)
    passed("Совместный поиск, категория, границы цены, наличие и сортировка")
    page.get_by_label("Поиск по названию").fill("Несуществующий товар")
    page.get_by_role("button", name="Применить").click()
    expect(page.get_by_role("heading", name="Товары не найдены")).to_be_visible()
    passed("Пустой результат поиска")
    page.goto(base + "/categories")
    page.screenshot(path=str(args.output / "06-categories.png"), full_page=True)
    row = page.get_by_role("row").filter(has=page.get_by_text("Письменные принадлежности", exact=True))
    row.get_by_role("link", name="Удалить категорию Письменные принадлежности").click()
    expect(page.get_by_role("heading", name="Категория используется")).to_be_visible()
    expect(page.get_by_role("button", name="Удалить категорию")).to_have_count(0)
    category_path = f"/categories/{cats['Письменные принадлежности']}"
    category_products = context.request.get(base + "/api/products", params={"category_id": cats["Письменные принадлежности"]}).json()
    assert category_products["total"] == len(category_products["items"])
    blocked = context.request.post(base + category_path + "/delete")
    preserved = {
        "http_status": blocked.status,
        "category_retained": context.request.get(base + "/api" + category_path).status == 200,
        "product_retained": context.request.get(base + "/api" + product_path).status == 200,
        "products_unchanged": context.request.get(base + "/api/products", params={"category_id": cats["Письменные принадлежности"]}).json() == category_products,
    }
    expected = {"http_status": 409, "category_retained": True, "product_retained": True, "products_unchanged": True}
    assert preserved == expected
    product_cases.append({
        "id": "delete_used_category",
        "name": "Удаление категории с товарами",
        "input": {"category": "Письменные принадлежности"},
        "expected": expected,
        "actual": preserved,
        "passed": True,
    })
    page.screenshot(path=str(args.output / "07-category-protection.png"), full_page=True)
    passed("Интерфейс блокирует удаление категории с товарами")
    page.goto(base + "/products")
    page.set_viewport_size({"width": 390, "height": 844})
    expect(page.get_by_role("button", name="Применить")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Страница выходит за ширину экрана"
    page.screenshot(path=str(args.output / "08-products-mobile.png"), full_page=True)
    page.goto(base + product_path + "/edit")
    expect(page.get_by_label("Название *", exact=True)).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path=str(args.output / "09-form-mobile.png"), full_page=True)
    passed("Мобильные список и форма: 390 px, без горизонтального скролла страницы")
    before_cancel = context.request.get(base + "/api" + product_path).json()
    page.goto(base + product_path + "/delete")
    page.get_by_role("link", name="Отмена", exact=True).click()
    expect(page.get_by_role("heading", name="Ручка шариковая синяя")).to_be_visible()
    after_cancel = context.request.get(base + "/api" + product_path)
    cancel_result = {"http_status": after_cancel.status, "record_unchanged": after_cancel.json() == before_cancel}
    assert cancel_result == {"http_status": 200, "record_unchanged": True}
    product_cases.append({
        "id": "cancel_product_deletion",
        "name": "Отмена удаления товара",
        "input": {"action": "Отмена"},
        "expected": {"http_status": 200, "record_unchanged": True},
        "actual": cancel_result,
        "passed": True,
    })
    passed("Отмена удаления сохраняет товар")
    page.goto(base + product_path + "/delete")
    page.get_by_role("button", name="Удалить товар", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Товар удалён")
    deleted_status = context.request.get(base + "/api" + product_path).status
    assert deleted_status == 404
    product_cases.append({
        "id": "delete_product",
        "name": "Подтверждённое удаление товара",
        "input": {"action": "Удалить товар"},
        "expected": {"http_status": 404},
        "actual": {"http_status": deleted_status},
        "passed": True,
    })
    page.get_by_role("status").screenshot(path=str(args.output / "12-product-deleted.png"))
    passed("Подтверждённое удаление через браузер")
    assert not errors, errors
    passed("Нет ошибок JavaScript в проверенных сценариях")
    context.close()
    # Обычные HTML-формы работают и при отключённом JavaScript.
    offline_js = browser.new_context(java_script_enabled=False)
    simple = offline_js.new_page()
    simple.goto(base + "/categories/new")
    simple.get_by_label("Название *", exact=True).fill("Категория без JavaScript")
    simple.get_by_role("button", name="Добавить категорию").click()
    expect(simple.get_by_role("status")).to_have_text("Категория добавлена")
    passed("Создание через HTML-форму без JavaScript")
    browser.close()

report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
          "browser": "Chromium", "browser_version": browser_version,
          "viewports": ["1440 × 1000", "390 × 844"], "data": "Учебный каталог на временной базе",
          "checks_passed": len(checks), "checks": checks,
          "temporary_database": True, "product_cases": product_cases}
(args.output / "browser-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False))
