"""Собрать 11 слайдов и текст выступления: python -m scripts.build_presentation."""

from datetime import datetime, timezone
import json
from pathlib import Path

from lxml import etree
from docx import Document
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
    text(item, relevance["problem"], .85, 1.72, 11.5, .65, 24, PLUM, True)
    text(item, relevance["number"], .85, 2.17, 4.9, 2.8, 144, ROSE, True)
    text(item, relevance["meaning"], 6.05, 2.92, 6.25, 1.5, 28, INK)
    for i, value in enumerate(relevance["theses"]):
        text(item, value, .95 + i * 4.04, 5.2, 3.75, .55, 21, MUTED)
    rect(item, .75, 6.02, 11.83, .66, PALE, rounded=True)
    text(item, relevance["conclusion"], .98, 6.16, 11.0, .48, 22, PLUM, True)
    text(item, relevance["source"], .85, 6.83, 11.5, .25, 10.5, MUTED)

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
        (7.2, 5.38, "ТОВАР", ["Идентификатор", "Артикул и название", "Категория", "Цена и остаток", "Описание и даты"]),
    ]:
        rect(item, x, 1.98, w, 3.8, WHITE, BORDER, True)
        rect(item, x, 1.98, w, .72, LILAC)
        text(item, label, x + .28, 2.17, w - .56, .37, 21, PLUM, True)
        for j, field in enumerate(fields):
            text(item, field, x + .28, 3.05 + j * .55, w - .56, .43, 23, INK)
    line = item.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(5.1), Inches(3.75), Inches(7.2), Inches(3.75))
    line.line.width = Pt(2)
    line.line.color.rgb = RGBColor.from_string(ROSE)
    text(item, "1 : N", 5.43, 3.05, 1.45, .5, 27, ROSE, True, PP_ALIGN.CENTER)
    for index, value in enumerate(["Артикул уникален", "Цена в копейках", "Остаток от нуля"]):
        x = .75 + index * 4.04
        rect(item, x, 6.13, 3.75, .6, PALE, rounded=True)
        text(item, value, x + .15, 6.26, 3.45, .33, 18, ROSE, True, PP_ALIGN.CENTER)

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
    rect(item, .75, 1.88, 3.25, 4.83, COVER, rounded=True)
    text(item, "154", 1.03, 2.65, 2.69, 1.65, 82, PLUM, True, PP_ALIGN.CENTER)
    text(item, "автоматических\nтеста пройдены", 1.03, 4.3, 2.69, 1.25, 23, PLUM, align=PP_ALIGN.CENTER)
    text(item, "Протокол: 29.10.2026", 1.03, 6.11, 2.69, .3, 13, MUTED, align=PP_ALIGN.CENTER)
    for i, (value, label) in enumerate([(35, "База данных"), (81, "JSON API"), (31, "HTML"), (7, "Загрузчик")]):
        y = 2.0 + i * .84
        text(item, label, 4.48, y, 3.2, .4, 21, INK)
        rect(item, 7.72, y + .08, 3.82, .24, BORDER, rounded=True)
        rect(item, 7.72, y + .08, 3.82 * value / 81, .24, ROSE, rounded=True)
        text(item, str(value), 11.7, y - .02, .65, .43, 23, ROSE, True, PP_ALIGN.RIGHT)
    text(item, "Chromium: 14 + 6 сценариев", 4.48, 5.73, 7.8, .52, 25, PLUM, True)
    text(item, "Отчёты: 21.10.2026", 4.48, 6.38, 7.8, .33, 14, MUTED)

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
    return OUTPUT


if __name__ == "__main__":
    print(build())
