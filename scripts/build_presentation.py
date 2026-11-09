"""Собрать слайды и текст защиты: python -m scripts.build_presentation."""

from datetime import datetime, timezone
import json
from pathlib import Path

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
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = WordPt(7)
    normal.paragraph_format.widow_control = True
    heading = document.styles["Heading 1"]
    heading.font.name = FONT
    heading.font.size = WordPt(14)
    heading.font.bold = True
    heading.font.color.rgb = WordColor.from_string(ROSE)
    heading.paragraph_format.space_before = WordPt(13)
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
    if len(content["slides"]) != 11 or len(content["conclusions"]) != 7:
        raise ValueError("Ожидаются 11 слайдов и выводы по семи задачам введения")
    goal, development = introduction.split(" Для этого необходимо ", 1)
    development, verification = development.split(" Проверка результата включает ", 1)
    development = "Для этого необходимо " + development
    verification = "Проверка результата включает " + verification

    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    properties = deck.core_properties
    properties.title = student["topic"]
    properties.author = student["student_name"]
    properties.subject = "Защита курсовой работы. 11 слайдов, выступление на 5–7 минут"
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
            text(item, f"{index:02d} / 11", 11.65, 7.08, .93, .25, 11, MUTED, align=PP_ALIGN.RIGHT)
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
        text(item, f"{index:02d} / 11", 11.5, 7.06, 1.08, .25, 11, MUTED, align=PP_ALIGN.RIGHT)
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
    for x, w, label, fields in [
        (.75, 4.35, "КАТЕГОРИЯ", ["Идентификатор", "Название", "Описание"]),
        (7.2, 5.38, "ТОВАР", ["Идентификатор", "Артикул и название", "Категория", "Цена и остаток", "Описание", "Дата создания", "Дата изменения"]),
    ]:
        rect(item, x, 1.98, w, 4.2, WHITE, BORDER, True)
        rect(item, x, 1.98, w, .72, LILAC)
        text(item, label, x + .28, 2.17, w - .56, .37, 21, PLUM, True)
        for j, field in enumerate(fields):
            text(item, field, x + .28, 2.92 + j * .455, w - .56, .45, 22, INK)
    line = item.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(5.1), Inches(3.75), Inches(7.2), Inches(3.75))
    line.line.width = Pt(2)
    line.line.color.rgb = RGBColor.from_string(ROSE)
    text(item, "1 : N", 5.43, 3.05, 1.45, .5, 27, ROSE, True, PP_ALIGN.CENTER)
    for index, value in enumerate(["Артикул уникален", "Цена в копейках", "Остаток от нуля"]):
        x = .75 + index * 4.04
        rect(item, x, 6.32, 3.75, .6, PALE, rounded=True)
        text(item, value, x + .15, 6.45, 3.45, .33, 18, ROSE, True, PP_ALIGN.CENTER)

    item = slide(6, "ОСНОВНАЯ ЧАСТЬ")
    stages = [("Браузер", "Форма товара"), ("FastAPI", "Проверка ввода"), ("catalog.py", "Операции"), ("SQLite", "Запись данных")]
    for i, (name, label) in enumerate(stages):
        x = .75 + i * 3.04
        rect(item, x, 2.65, 2.7, 2.05, PALE if i == 2 else WHITE, BORDER, True)
        text(item, name, x + .18, 3.05, 2.34, .55, 26, PLUM, True, PP_ALIGN.CENTER)
        text(item, label, x + .18, 3.91, 2.34, .55, 18, MUTED, align=PP_ALIGN.CENTER)
        if i < 3:
            arrow = item.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.75), Inches(3.48), Inches(.24), Inches(.28))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = RGBColor.from_string(ROSE)
            arrow.line.fill.background()
    text(item, "Успех записи: commit", .97, 5.55, 5.5, .55, 24, ROSE, True)
    text(item, "Конфликт записи: rollback", 6.75, 5.55, 5.6, .55, 24, MUTED, True)

    item = slide(7, "ОСНОВНАЯ ЧАСТЬ")
    image = DIRECTORY / "figures/catalog-2026-11-08.png"
    item.shapes.add_picture(str(image), Inches(1.34), Inches(1.72), width=Inches(10.65))
    text(item, "Учебный каталог. Снимок текущего интерфейса от 08.11.2026", .85, 6.91, 10.6, .2, 10, MUTED)

    item = slide(8, "ОСНОВНАЯ ЧАСТЬ")
    conditions = ["РУЧКА", "Категория: ручки", "49,90–100,00 руб.", "В наличии"]
    for i, value in enumerate(conditions):
        x = .75 + i * 3.04
        rect(item, x, 1.88, 2.7, .75, PALE, rounded=True)
        text(item, value, x + .12, 2.1, 2.46, .38, 19, ROSE, True, PP_ALIGN.CENTER)
    columns = [.98, 6.2, 8.04, 9.8]
    for x, label, w in zip(columns, ["Позиция", "Цена, руб.", "Остаток", "Результат"], [5, 1.7, 1.6, 2.5]):
        text(item, label, x, 2.99, w, .38, 17, MUTED, True)
    rows = [
        ("Ручка синяя", "49,90", "20", "Входит", True),
        ("Ручка гелевая", "100,00", "3", "Входит", True),
        ("РУЧКА красная", "99,00", "0", "Нет остатка", False),
        ("Тетрадь", "20,00", "4", "Исключена", False),
    ]
    for i, row in enumerate(rows):
        y = 3.53 + i * .7
        rect(item, .75, y, 11.83, .61, WHITE if row[4] else RED_PALE, rounded=True)
        for x, value, w in zip(columns, row[:4], [5.0, 1.7, 1.6, 2.5]):
            text(item, value, x, y + .12, w, .4, 21, INK if row[4] else RED, x == columns[-1])
    text(item, "Результат: 2 позиции", .98, 6.51, 11.0, .43, 24, ROSE, True)

    item = slide(9, "ОСНОВНАЯ ЧАСТЬ")
    evidence = json.loads((ROOT / content["product_testing"]["report"]).read_text())
    cases = evidence["product_cases"]
    if len(cases) != 3 or any(not case["passed"] or case["expected"] != case["actual"] for case in cases):
        raise ValueError("Для слайда нужны три подтверждённые проверки продукта")
    checked_date = datetime.fromisoformat(evidence["checked_at_utc"]).strftime("%d.%m.%Y")
    text(item, f"Chromium · временная база · {checked_date}", .98, 1.72, 11.1, .33, 16, MUTED)
    columns = [.98, 4.85, 8.74]
    for x, label in zip(columns, ["Действие", "Ожидалось", "Получено"]):
        text(item, label, x, 2.14, 3.5, .36, 17, MUTED, True)
    price = cases[0]["actual"]["price"].replace(".", ",")
    quantity = cases[0]["actual"]["quantity"]
    saved_price = cases[1]["actual"]["saved_price"].replace(".", ",")
    invalid_price = cases[1]["input"]["price"]
    rows = [
        (f"Создать товар:\n{price} руб., {quantity} шт.", "Сохранить цену\nи остаток", f"{price} руб., {quantity} шт.\nсохранены"),
        (f"Указать цену {invalid_price}", "Отклонить,\nсохранить запись", f"Ошибка; {saved_price} руб.\nбез изменений"),
        ("Удалить категорию\nс товарами", "Сохранить категорию\nи товары", "Удаление отклонено;\nзаписи сохранены"),
    ]
    for index, values in enumerate(rows):
        y = 2.62 + index * .97
        rect(item, .75, y, 11.83, .90, WHITE if index % 2 == 0 else PALE, rounded=True)
        for column, (x, value) in enumerate(zip(columns, values)):
            text(item, value, x, y + .08, 3.5, .82, 20, ROSE if column == 0 else INK, column != 1)
    item.shapes.add_picture(str(ROOT / content["product_testing"]["screenshot"]), Inches(.98), Inches(5.7), width=Inches(11.37))
    text(item, f"154 автотеста: 29.10.2026; {evidence['checks_passed']} сценариев Chromium: {checked_date}", .98, 6.68, 11.1, .32, 13, MUTED)

    item = slide(10, "РЕЗУЛЬТАТЫ")
    text(item, "Задача", .98, 1.94, 3.6, .34, 17, MUTED, True)
    text(item, "Полученный результат", 4.8, 1.94, 7.5, .34, 17, MUTED, True)
    for i, (task, result) in enumerate(content["conclusions"]):
        y = 2.48 + i * .59
        rect(item, .75, y, 11.83, .54, WHITE if i % 2 == 0 else PALE, rounded=True)
        text(item, task, .98, y + .09, 3.6, .4, 18, ROSE, True)
        text(item, result, 4.8, y + .09, 7.5, .4, 18, INK)

    cover(11, closing=True)
    for item in deck.slides:
        for shape in item.shapes:
            sp_pr = getattr(shape._element, "spPr", None)
            if sp_pr is not None:
                sp_pr.append(etree.Element("{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst"))
            effect_ref = shape._element.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}effectRef")
            if effect_ref is not None:
                effect_ref.set("idx", "0")
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
