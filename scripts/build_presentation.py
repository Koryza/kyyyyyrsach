"""Собрать слайды и текст защиты: python -m scripts.build_presentation."""

from datetime import datetime, timezone
from collections import Counter
import json
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image
from lxml import etree
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt as WordPt, RGBColor as WordColor
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from scripts.presentation_design import apply_design

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / "docs" / "defense"
OUTPUT = DIRECTORY / "catalog_defense.pptx"
PLUM, ROSE, INK = "583C64", "A3567A", "493B50"
MUTED, BACK, WHITE, BORDER = "726078", "FFF8FC", "FFFFFF", "EADDE9"
PALE, RED, RED_PALE = "F0E8F7", "A44F68", "FBE9F0"
COVER, LILAC = "F8E3EE", "E9DFF2"
FONT = "Arial"


def write_speech(content, student):
    """Сохранить текст выступления в Word для чтения и печати."""
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(1.8)
    section.left_margin = section.right_margin = Cm(2)
    normal = document.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = WordPt(12)
    normal.font.color.rgb = WordColor.from_string(INK)
    normal.paragraph_format.line_spacing = 1.1
    normal.paragraph_format.space_after = WordPt(5)
    normal.paragraph_format.widow_control = True
    heading = document.styles["Heading 1"]
    heading.font.name = FONT
    heading.font.size = WordPt(14)
    heading.font.bold = True
    heading.font.color.rgb = WordColor.from_string(ROSE)
    heading.paragraph_format.space_before = WordPt(10)
    heading.paragraph_format.space_after = WordPt(4)
    heading.paragraph_format.keep_with_next = True

    title = document.add_paragraph()
    title.paragraph_format.keep_with_next = True
    run = title.add_run("Текст защиты курсового проекта")
    run.bold, run.font.size = True, WordPt(18)
    run.font.color.rgb = WordColor.from_string(PLUM)
    document.add_paragraph(student["topic"])
    document.add_paragraph(f"{student['student_name']}, группа {student['group_short']}")
    total = sum(item["seconds"] for item in content["slides"])
    document.add_paragraph(
        f"План с паузами и переходами: {total // 60} мин {total % 60:02d} с. "
        "Это ориентир для репетиции; фактическое время нужно проверить с таймером."
    )

    elapsed = 0
    for index, item in enumerate(content["slides"], 1):
        end = elapsed + item["seconds"]
        document.add_heading(f"Слайд {index}. {item['title']}", level=1)
        timing = document.add_paragraph(
            f"План: {elapsed // 60}:{elapsed % 60:02d}–{end // 60}:{end % 60:02d}."
        )
        timing.paragraph_format.keep_with_next = True
        timing.runs[0].font.size = WordPt(10)
        timing.runs[0].font.color.rgb = WordColor.from_string(MUTED)
        paragraphs = item["notes"].split("\n\n")
        for offset, value in enumerate(paragraphs):
            paragraph = document.add_paragraph(value)
            paragraph.paragraph_format.keep_together = True
            paragraph.paragraph_format.keep_with_next = offset < len(paragraphs) - 1
        elapsed = end

    footer = section.footer.paragraphs[0]
    footer.paragraph_format.alignment = 2
    run = footer.add_run()
    run.font.name, run.font.size = FONT, WordPt(10)
    page_number = OxmlElement("w:fldSimple")
    page_number.set(qn("w:instr"), "PAGE")
    run._r.addnext(page_number)
    document.core_properties.title = "Текст защиты курсового проекта"
    document.core_properties.author = student["student_name"]
    document.core_properties.last_modified_by = "Сборка проекта"
    document.core_properties.created = document.core_properties.modified = datetime.now(timezone.utc)
    document.save(DIRECTORY / "Текст_защиты.docx")


def build():
    content = json.loads((DIRECTORY / "presentation.json").read_text())
    student = json.loads((ROOT / "docs/coursework/student.json").read_text())
    introduction = next(
        paragraph.text
        for paragraph in Document(ROOT / content["introduction_source"]).paragraphs
        if paragraph.text.startswith("Цель работы —")
    )
    if introduction != content["introduction_paragraph"]:
        raise ValueError("Введение изменилось: нужно согласовать цель, задачи и выводы слайдов")
    slide_count = len(content["slides"])
    if slide_count != 15 or len(content["conclusions"]) != 7:
        raise ValueError("Ожидаются 15 слайдов и выводы по семи задачам введения")
    goal, development = introduction.split(" Для этого необходимо ", 1)
    development, verification = development.split(" Проверка результата включает ", 1)
    development = "Для этого необходимо " + development
    verification = "Проверка результата включает " + verification

    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    properties = deck.core_properties
    properties.title = student["topic"]
    properties.author = student["student_name"]
    properties.subject = f"Защита курсовой работы. {slide_count} слайдов, выступление на 5–7 минут"
    properties.last_modified_by = "Сборка презентации"
    properties.created = properties.modified = datetime.now(timezone.utc)

    def rect(slide, x, y, w, h, fill=WHITE, border=None, rounded=False):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
            Inches(x), Inches(y), Inches(w), Inches(h),
        )
        if rounded:
            shape.adjustments[0] = 0.08
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(fill)
        if border:
            shape.line.color.rgb = RGBColor.from_string(border)
            shape.line.width = Pt(0.8)
        else:
            shape.line.fill.background()
        return shape

    def text(slide, value, x, y, w, h, size=24, color=INK, bold=False, align=PP_ALIGN.LEFT):
        shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        frame = shape.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = 0
        frame.margin_top = frame.margin_bottom = 0
        frame.vertical_anchor = MSO_ANCHOR.TOP
        for index, line in enumerate(value.split("\n")):
            p = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            p.text = line
            p.font.name, p.font.size = FONT, Pt(size)
            p.font.bold = bold
            p.font.color.rgb = RGBColor.from_string(color)
            p.alignment = align
            p.line_spacing = 1.12
            p.space_before = Pt(0)
            p.space_after = Pt(7)
        return shape

    def screenshot(slide, path, x, y, width, region=None):
        # Кадрирование в PowerPoint сохраняет исходный снимок внутри файла.
        with Image.open(path) as original:
            image_width, image_height = original.size
        left, top, right, bottom = region or (0, 0, image_width, image_height)
        height = width * (bottom - top) / (right - left)
        shape = slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(width), height=Inches(height))
        shape.crop_left, shape.crop_top = left / image_width, top / image_height
        shape.crop_right, shape.crop_bottom = 1 - right / image_width, 1 - bottom / image_height
        return shape

    def slide(index, section=None):
        item = deck.slides.add_slide(deck.slide_layouts[6])
        item.background.fill.solid()
        item.background.fill.fore_color.rgb = RGBColor.from_string(BACK)
        item.notes_slide.notes_text_frame.text = content["slides"][index - 1]["notes"]
        if section:
            text(item, section, .75, .25, 10, .3, 11, ROSE, True)
            text(item, content["slides"][index - 1]["title"], .75, .68, 11.7, .65, 31, PLUM, True)
            rect(item, .75, 1.48, 11.83, .018, BORDER)
            text(item, "МФЮА  /  Чемоданов Н. С.", .75, 7.10, 9.8, .22, 10, MUTED)
            text(item, f"{index:02d} / {slide_count}", 11.65, 7.08, .93, .25, 11, MUTED, align=PP_ALIGN.RIGHT)
        return item

    def cover(index, closing=False):
        item = slide(index)
        rect(item, 0, 0, 13.333, 7.5, COVER)
        rect(item, .75, 1.45, 1.1, .055, ROSE)
        text(item, "Московский финансово-юридический университет МФЮА", .75, .45, 11.8, .5, 21, PLUM)
        text(item, "КУРСОВОЙ ПРОЕКТ", .75, 1.02, 11.5, .28, 12, MUTED, True)
        text(item, "Разработка модуля управления\nкаталогом товаров\nдля интернет-магазина", .75, 1.9, 11.9, 2.5, 38, PLUM, True)
        if closing:
            text(item, "Спасибо за внимание", .75, 4.25, 11.6, .6, 28, ROSE, True)
        text(item, "Выполнил", .75, 5.12, 5.5, .3, 13, MUTED)
        text(item, student["student_name"], .75, 5.51, 6.0, .8, 23, PLUM, True)
        text(item, f"Группа {student['group']} ({student['group_short']}), {student['course']}-й курс", .75, 6.35, 6.0, .32, 16, MUTED)
        text(item, "Руководитель", 7.15, 5.12, 5.4, .3, 13, MUTED)
        text(item, student["supervisor"], 7.15, 5.51, 5.4, .9, 23, PLUM, True)
        text(item, f"{student['city']}, {student['year']}", .75, 7.04, 10, .3, 14, MUTED)
        text(item, f"{index:02d} / {slide_count}", 11.5, 7.06, 1.08, .25, 11, MUTED, align=PP_ALIGN.RIGHT)
        return item

    cover(1)

    item = slide(2, "ПОСТАНОВКА ЗАДАЧИ")
    relevance = content["relevance"]
    text(item, relevance["headline"], .85, 2.03, 6.3, 1.85, 94, ROSE, True)
    text(item, relevance["context"], .92, 3.92, 6.5, .72, 36, PLUM, True)
    rect(item, 7.65, 2.13, 4.93, 2.63, WHITE, BORDER, rounded=True)
    text(item, "ПРОБЛЕМА", 7.95, 2.43, 4.3, .28, 11, ROSE, True)
    text(item, relevance["problem"], 7.95, 2.98, 4.28, 1.55, 23, INK)
    for i, value in enumerate(relevance["theses"]):
        x = .95 + i * 4.04
        rect(item, x, 5.2, .48, .035, ROSE)
        text(item, value, x, 5.43, 3.75, .55, 21, MUTED)
    rect(item, .75, 6.25, 11.83, .59, PALE, rounded=True)
    text(item, relevance["conclusion"], .98, 6.37, 11.0, .48, 22, PLUM, True)

    item = slide(3, "ПОСТАНОВКА ЗАДАЧИ")
    rect(item, .75, 1.85, 11.83, 1.4, COVER, rounded=True)
    text(item, goal, 1.05, 2.1, 11.2, .95, 26, PLUM, True)
    for x, w, label, value in [
        (.75, 6.25, "Разработка", development),
        (7.28, 5.3, "Проверка", verification),
    ]:
        rect(item, x, 3.55, w, 3.15, WHITE, BORDER, True)
        text(item, label, x + .28, 3.82, w - .56, .4, 20, ROSE, True)
        text(item, value, x + .28, 4.27, w - .56, 2.25, 20, INK)

    item = slide(4, "ПРЕДМЕТНАЯ ОБЛАСТЬ")
    concepts = [
        ("Товарная позиция", "Запись о товаре с собственным артикулом, ценой и остатком."),
        ("Категория", "Группа товаров, объединённых по назначению."),
        ("Артикул", "Уникальное обозначение товарной позиции."),
    ]
    for index, (name, definition) in enumerate(concepts):
        y = 1.9 + index * 1.6
        rect(item, .75, y, 11.83, 1.35, WHITE, BORDER, True)
        rect(item, .75, y, .055, 1.35, ROSE)
        text(item, name, 1.03, y + .27, 3.8, .8, 25, ROSE, True)
        text(item, definition, 5.0, y + .27, 7.18, .9, 24, INK)

    item = slide(5, "ОСНОВНАЯ ЧАСТЬ")
    for x, w, height, label, fields in [
        (.75, 4.35, 2.28, "КАТЕГОРИЯ", ["Идентификатор", "Название", "Описание"]),
        (7.2, 5.38, 4.93, "ТОВАР", ["Идентификатор", "Артикул", "Название", "Идентификатор категории", "Цена в копейках", "Остаток", "Описание", "Дата создания", "Дата изменения"]),
    ]:
        rect(item, x, 1.9, w, height, WHITE, BORDER, True)
        rect(item, x, 1.9, w, .55, LILAC)
        text(item, label, x + .28, 2.02, w - .56, .4, 21, PLUM, True)
        for j, field in enumerate(fields):
            text(item, field, x + .28, 2.68 + j * .44, w - .56, .43, 21, INK)
    line = item.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(5.1), Inches(3.15), Inches(7.2), Inches(3.15))
    line.line.width = Pt(2)
    line.line.color.rgb = RGBColor.from_string(ROSE)
    text(item, "1 : N", 5.43, 2.58, 1.45, .5, 27, ROSE, True, PP_ALIGN.CENTER)
    text(item, "Пример: три товара одной категории", .85, 4.48, 6.0, .4, 19, ROSE, True)
    text(item, "Категория № 1 — письменные принадлежности", .85, 4.94, 6.0, .3, 14, MUTED)
    text(item, "Товар", 1.0, 5.36, 4.6, .3, 16, MUTED, True)
    text(item, "Категория", 5.48, 5.36, 1.2, .3, 15, MUTED, True)
    for index, name in enumerate(["Ручка синяя", "Ручка красная", "Ручка гелевая"]):
        y = 5.78 + index * .36
        rect(item, .85, y, 5.98, .33, WHITE if index % 2 == 0 else PALE, rounded=True)
        text(item, name, 1.0, y + .02, 4.35, .3, 16, INK)
        text(item, "1", 5.48, y + .02, 1.2, .3, 16, PLUM, True)

    item = slide(6, "ОСНОВНАЯ ЧАСТЬ")
    product_images = content["product_screenshots"]
    text(item, "Карточка товара", .85, 1.73, 6.35, .4, 20, ROSE, True)
    text(item, "Форма редактирования", 7.65, 1.73, 4.72, .4, 20, ROSE, True)
    screenshot(item, ROOT / product_images["detail"], .85, 2.18, 6.35, (260, 226, 1416, 805))
    screenshot(item, ROOT / product_images["form"], 7.65, 2.18, 4.72, (276, 276, 1106, 1016))
    text(item, "Цена, остаток и даты", .98, 5.64, 6.25, .45, 23, PLUM, True)
    text(item, "Из карточки открывается редактирование", .98, 6.12, 6.25, .35, 17, MUTED)
    for i, name in enumerate(["Браузер", "FastAPI", "catalog.py", "SQLite"]):
        x = .75 + i * 3.04
        rect(item, x, 6.62, 2.7, .37, PALE, rounded=True)
        text(item, name, x + .12, 6.66, 2.46, .29, 16, PLUM, True, PP_ALIGN.CENTER)
        if i < 3:
            arrow = item.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.75), Inches(6.72), Inches(.24), Inches(.16))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = RGBColor.from_string(ROSE)
            arrow.line.fill.background()

    item = slide(7, "ОСНОВНАЯ ЧАСТЬ")
    image = DIRECTORY / "figures/catalog-2026-11-08.png"
    item.shapes.add_picture(str(image), Inches(1.34), Inches(1.72), width=Inches(10.65))
    text(item, "Учебный каталог. Снимок текущего интерфейса от 08.11.2026", .85, 6.91, 10.6, .2, 10, MUTED)

    item = slide(8, "ОСНОВНАЯ ЧАСТЬ")
    screenshot(item, ROOT / product_images["filters"], 1.51, 1.77, 10.3, (276, 232, 1402, 746))
    rect(item, .85, 6.54, 11.63, .44, PALE, rounded=True)
    text(item, "«РУЧКА» · 50–80 руб. · в наличии · найдено 2 товара", 1.03, 6.6, 11.27, .34, 19, PLUM, True)

    item = slide(9, "ТЕСТИРОВАНИЕ")
    evidence = json.loads((ROOT / content["product_testing"]["report"]).read_text())
    cases = {case["id"]: case for case in evidence["product_cases"]}
    if len(cases) != 6 or any(not case["passed"] or case["expected"] != case["actual"] for case in cases.values()):
        raise ValueError("Для слайдов нужны шесть подтверждённых проверок продукта")
    checked_date = datetime.fromisoformat(evidence["checked_at_utc"]).strftime("%d.%m.%Y")
    text(item, "Для каждого сценария: ожидалось и получено", .98, 1.98, 11.2, .6, 25, PLUM, True)
    steps = [("Действие", "Форма в браузере"), ("Ответ", "Сообщение и HTTP-код"), ("Данные", "Проверка через API")]
    for index, (name, label) in enumerate(steps):
        x = .75 + index * 4.04
        rect(item, x, 3.0, 3.75, 2.0, WHITE, BORDER, True)
        text(item, name, x + .2, 3.35, 3.35, .6, 29, ROSE, True, PP_ALIGN.CENTER)
        text(item, label, x + .2, 4.2, 3.35, .45, 19, INK, align=PP_ALIGN.CENTER)
        if index < 2:
            arrow = item.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 3.81), Inches(3.85), Inches(.16), Inches(.2))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = RGBColor.from_string(ROSE)
            arrow.line.fill.background()
    text(item, "Отдельная временная SQLite-база", .98, 5.75, 11.2, .5, 24, PLUM, True)
    text(item, f"Chromium · {checked_date}", .98, 6.45, 11.2, .35, 16, MUTED)

    item = slide(10, "ТЕСТИРОВАНИЕ")
    for x, label, width in [(.98, "Операция", 1.6), (2.72, "Ожидалось", 1.55), (4.46, "Получено", 1.55)]:
        text(item, label, x, 2.0, width, .35, 15, MUTED, True)
    created, updated = cases["create_product"]["actual"], cases["update_product"]["actual"]
    rows = [
        ("Добавить", f"{created['price'].replace('.', ',')} руб.\n{created['quantity']} шт.", f"{created['price'].replace('.', ',')} руб.\n{created['quantity']} шт."),
        ("Изменить", f"{updated['price'].replace('.', ',')} руб.\n{updated['quantity']} шт.", f"{updated['price'].replace('.', ',')} руб.\n{updated['quantity']} шт."),
        ("Удалить", "Запись\nнедоступна", f"{cases['delete_product']['actual']['http_status']}:\nне найден"),
    ]
    for index, values in enumerate(rows):
        y = 2.5 + index * 1.06
        rect(item, .75, y, 5.42, .95, WHITE if index % 2 == 0 else PALE, rounded=True)
        for column, (x, value) in enumerate(zip([.98, 2.72, 4.46], values)):
            text(item, value, x, y + .14, 1.6, .75, 17, ROSE if column == 0 else INK, column != 1)
    text(item, "Карточка после изменения", 6.55, 1.96, 6.0, .4, 20, ROSE, True)
    screenshot(item, ROOT / product_images["updated"], 6.55, 2.5, 6.0, (260, 226, 1416, 805))
    text(item, "Сообщение после удаления", 6.55, 5.65, 6.0, .3, 15, MUTED)
    screenshot(item, ROOT / product_images["deleted"], 6.55, 6.02, 4.5)
    text(item, "Отмена удаления:\nтовар сохранён (200).", .98, 6.13, 5.1, .68, 16, PLUM, True)

    item = slide(11, "ТЕСТИРОВАНИЕ")
    invalid_case = cases["invalid_price"]
    text(item, "Ввод в поле «Цена»", .98, 1.93, 5.2, .4, 20, MUTED)
    text(item, invalid_case["input"]["price"], .98, 2.5, 5.2, 1.35, 68, ROSE, True)
    text(item, "Ожидалось", .98, 4.15, 5.1, .35, 16, MUTED, True)
    text(item, "Отказ без изменения записи", .98, 4.6, 5.1, .9, 23, PLUM, True)
    text(item, "Получено", .98, 5.65, 5.1, .35, 16, MUTED, True)
    text(item, f"{invalid_case['actual']['http_status']}: прежние данные сохранены", .98, 6.1, 5.1, .7, 22, PLUM, True)
    text(item, "Фрагменты формы после отказа", 6.5, 1.93, 6.0, .4, 19, ROSE, True)
    screenshot(item, ROOT / content["product_testing"]["screenshot"], 6.5, 2.58, 6.1)
    screenshot(item, ROOT / product_images["invalid"], 6.5, 3.4, 6.1, (276, 832, 1106, 1118))
    saved_price = invalid_case["actual"]["saved_price"].replace(".", ",")
    text(item, f"В базе: {saved_price} руб.; 24 шт.", 6.5, 5.95, 6.0, .55, 23, PLUM, True)

    item = slide(12, "ТЕСТИРОВАНИЕ")
    text(item, "Ожидалось", .98, 1.98, 4.2, .4, 17, MUTED, True)
    text(item, "Отказ в удалении.\nСвязи сохранены.", .98, 2.54, 4.2, 1.2, 24, PLUM, True)
    text(item, str(cases["delete_used_category"]["actual"]["http_status"]), .98, 3.94, 4.2, 1.3, 66, ROSE, True)
    text(item, "Категория и товары\nсохранены", .98, 5.35, 4.2, .95, 22, PLUM, True)
    text(item, "Сообщение приложения", 5.5, 1.98, 7.0, .4, 20, ROSE, True)
    screenshot(item, ROOT / product_images["category"], 5.5, 2.62, 7.0, (276, 156, 966, 470))
    text(item, "Проверено через API: состав товаров не изменился", .98, 6.55, 11.3, .4, 19, PLUM, True)

    item = slide(13, "ТЕСТИРОВАНИЕ")
    automatic = ElementTree.parse(ROOT / content["product_testing"]["automated_report"]).getroot()
    tests = automatic.findall(".//testcase")
    if not tests or automatic.findall(".//failure") or automatic.findall(".//error") or automatic.findall(".//skipped"):
        raise ValueError("В протоколе автоматических тестов есть непройденные проверки")
    counts = Counter(test.get("classname") for test in tests)
    rect(item, .75, 1.88, 3.25, 4.85, COVER, rounded=True)
    text(item, str(len(tests)), 1.03, 2.7, 2.69, 1.65, 82, PLUM, True, PP_ALIGN.CENTER)
    text(item, "автоматических\nтеста пройдены", 1.03, 4.34, 2.69, 1.25, 23, PLUM, align=PP_ALIGN.CENTER)
    text(item, checked_date, 1.03, 6.15, 2.69, .3, 14, MUTED, align=PP_ALIGN.CENTER)
    groups = [("tests.test_database", "База данных"), ("tests.test_api", "JSON API"), ("tests.test_pages", "HTML"), ("tests.test_demo_data", "Загрузчик")]
    for index, (key, label) in enumerate(groups):
        y = 2.0 + index * .84
        text(item, label, 4.48, y, 3.2, .4, 21, INK)
        rect(item, 7.72, y + .08, 3.82, .24, BORDER, rounded=True)
        rect(item, 7.72, y + .08, 3.82 * counts[key] / max(counts.values()), .24, ROSE, rounded=True)
        text(item, str(counts[key]), 11.7, y - .02, .65, .43, 23, ROSE, True, PP_ALIGN.RIGHT)
    text(item, f"{evidence['checks_passed']} сценариев Chromium пройдены", 4.48, 5.71, 7.8, .6, 24, PLUM, True)
    text(item, "6 подробных проверок входят в число 14", 4.48, 6.43, 7.8, .32, 15, MUTED)

    item = slide(14, "РЕЗУЛЬТАТЫ")
    text(item, "Задача", .98, 1.94, 3.6, .34, 17, MUTED, True)
    text(item, "Полученный результат", 4.8, 1.94, 7.5, .34, 17, MUTED, True)
    for i, (task, result) in enumerate(content["conclusions"]):
        y = 2.48 + i * .59
        rect(item, .75, y, 11.83, .54, WHITE if i % 2 == 0 else PALE, rounded=True)
        text(item, task, .98, y + .09, 3.6, .4, 18, ROSE, True)
        text(item, result, 4.8, y + .09, 7.5, .4, 18, INK)

    cover(15, closing=True)
    for item in deck.slides:
        for shape in item.shapes:
            sp_pr = getattr(shape._element, "spPr", None)
            if sp_pr is not None:
                sp_pr.append(etree.Element("{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst"))
            effect_ref = shape._element.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}effectRef")
            if effect_ref is not None:
                effect_ref.set("idx", "0")
    apply_design(deck)
    deck.save(OUTPUT)

    # Отдельный редактируемый слайд актуальности для вставки в презентацию.
    single = Presentation(OUTPUT)
    keep = single.slides._sldIdLst[1]
    for entry in list(single.slides._sldIdLst):
        if entry is not keep:
            single.part.drop_rel(entry.rId)
            single.slides._sldIdLst.remove(entry)
    single.core_properties.title = "Актуальность темы: модуль управления каталогом товаров"
    single.save(DIRECTORY / "relevance_slide.pptx")

    total = sum(s["seconds"] for s in content["slides"])
    notes = [
        "# Текст выступления по слайдам",
        "",
        f"План: {total // 60} мин {total % 60:02d} с. Это ориентир для репетиции, а не замер речи. "
        "Время включает паузы и переходы; фактическую длительность нужно проверить с таймером.",
        "",
    ]
    elapsed = 0
    for i, data in enumerate(content["slides"], 1):
        end = elapsed + data["seconds"]
        notes.extend([
            f"## {i}. {data['title']}", "",
            f"План: {elapsed // 60}:{elapsed % 60:02d}–{end // 60}:{end % 60:02d}.", "",
            data["notes"], "",
        ])
        elapsed = end
    (DIRECTORY / "SPEAKER_NOTES.md").write_text("\n".join(notes))
    write_speech(content, student)
    return OUTPUT


if __name__ == "__main__":
    print(build())
