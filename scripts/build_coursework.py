"""Собрать редактируемые DOCX и PPTX из материалов проекта.

Необязательные зависимости: requirements-docs.txt. Из корня: python -m scripts.build_coursework
PDF получается отдельным экспортом LibreOffice/Word/PowerPoint; это не часть сервера.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt as WordPt, RGBColor as WordColor

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WORD_FILE = DOCS / "coursework" / "coursework_draft.docx"
SLIDES_FILE = DOCS / "defense" / "catalog_defense.pptx"
STUDENT = json.loads((DOCS / "coursework" / "student.json").read_text())


def plain(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.replace("**", "").replace("`", "")


def field(paragraph, instruction, cached=""):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar"); begin.set(qn("w:fldCharType"), "begin")
    code = OxmlElement("w:instrText"); code.set(qn("xml:space"), "preserve"); code.text = instruction
    separate = OxmlElement("w:fldChar"); separate.set(qn("w:fldCharType"), "separate")
    value = OxmlElement("w:t"); value.text = cached
    end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end")
    for element in (begin, code, separate, value, end): run._r.append(element)


def make_word():
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin, section.right_margin = Mm(30), Mm(10)
    section.top_margin = section.bottom_margin = Mm(20)
    section.header_distance = Mm(10)
    section.different_first_page_header_footer = True
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = "Times New Roman", WordPt(14)
    for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        normal._element.rPr.rFonts.attrib.pop(qn("w:" + attribute), None)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:cs"), "Times New Roman")
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.first_line_indent = Mm(12.5)
    normal.paragraph_format.space_after = WordPt(0)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for name in ("Heading 1", "Heading 2"):
        style = document.styles[name]
        style.font.name, style.font.size, style.font.bold = "Times New Roman", WordPt(14), True
        style.font.color.rgb = WordColor(0, 0, 0)
        for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
            style._element.rPr.rFonts.attrib.pop(qn("w:" + attribute), None)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:cs"), "Times New Roman")
        style.paragraph_format.first_line_indent = Mm(0)
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style.paragraph_format.space_before = WordPt(18)
        style.paragraph_format.space_after = WordPt(14)
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.keep_with_next = True
    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header.paragraph_format.first_line_indent = Mm(0)
    field(header, " PAGE ")

    def cover(text, *, bold=False, before=0, after=0, size=14, align=WD_ALIGN_PARAGRAPH.CENTER):
        paragraph = document.add_paragraph()
        paragraph.alignment = align
        paragraph.paragraph_format.first_line_indent = Mm(0)
        paragraph.paragraph_format.line_spacing = 1.1
        paragraph.paragraph_format.space_before = WordPt(before)
        paragraph.paragraph_format.space_after = WordPt(after)
        run = paragraph.add_run(text); run.bold = bold; run.font.size = WordPt(size)

    cover("Аккредитованное образовательное частное учреждение\nвысшего образования")
    cover("«Московский финансово-юридический университет МФЮА»\n(МФЮА)", bold=True)
    cover(f"КАФЕДРА «{STUDENT['department'].upper()}»", before=14)
    cover("КУРСОВАЯ РАБОТА", bold=True, before=35, after=12)
    cover(f"по дисциплине: «{STUDENT['discipline']}»", after=12)
    cover("на тему: «Разработка модуля управления каталогом\nтоваров для интернет-магазина»", bold=True, after=25)
    cover(f"Специальность: {STUDENT['specialty_code']}\n{STUDENT['specialty']}\nПрофиль: {STUDENT['profile']}", align=WD_ALIGN_PARAGRAPH.LEFT, after=18)
    cover(f"Автор работы: {STUDENT['student_name']}\nКурс: {STUDENT['course']}       Группа: {STUDENT['group']} ({STUDENT['group_short']})\nРуководитель работы: {STUDENT['supervisor']}\nПодписи и даты: ________________________", align=WD_ALIGN_PARAGRAPH.LEFT, after=25)
    cover(f"{STUDENT['city']} — {STUDENT['year']}", before=25)
    document.add_page_break()
    document.add_heading("СОДЕРЖАНИЕ", 1)
    toc_anchor = document.add_paragraph()
    headings = []
    document.add_page_break()

    def heading(title, level=1):
        paragraph = document.add_heading(title.upper(), level)
        if level == 1 and headings: paragraph.paragraph_format.page_break_before = True
        bookmark = f"chapter_{len(headings) + 1}"
        start = OxmlElement("w:bookmarkStart"); start.set(qn("w:id"), str(100 + len(headings))); start.set(qn("w:name"), bookmark)
        end = OxmlElement("w:bookmarkEnd"); end.set(qn("w:id"), str(100 + len(headings)))
        paragraph._p.insert(0, start); paragraph._p.append(end)
        headings.append((title, bookmark, level))

    def table(caption, headers, rows, widths):
        paragraph = document.add_paragraph(caption)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.first_line_indent = Mm(0)
        paragraph.paragraph_format.space_before = WordPt(12)
        paragraph.paragraph_format.keep_with_next = True
        grid = document.add_table(rows=1, cols=len(headers))
        grid.style = "Table Grid"
        grid.autofit = False
        for column, width in zip(grid.columns, widths): column.width = Mm(width)
        repeating = OxmlElement("w:tblHeader")
        grid.rows[0]._tr.get_or_add_trPr().append(repeating)
        for cell, value in zip(grid.rows[0].cells, headers): cell.text = value
        for row in rows:
            for cell, value in zip(grid.add_row().cells, row): cell.text = value
        for row_index, row in enumerate(grid.rows):
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            for cell, width in zip(row.cells, widths):
                cell.width = Mm(width)
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.first_line_indent = Mm(0)
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    paragraph.paragraph_format.keep_with_next = row_index < len(grid.rows) - 1
                    for run in paragraph.runs:
                        run.font.name = "Times New Roman"
                        run.font.size = WordPt(14)
                        run.bold = row_index == 0
        document.add_paragraph()

    def diagram(kind):
        if kind == "model":
            values = ["КАТЕГОРИЯ\nid (PK)\nname\nname_normalized\ndescription", "1 : N\n→", "ТОВАР\nid (PK) · sku (UQ)\ncategory_id (FK)\nname · description\nprice_kopecks · quantity\ncreated_at · updated_at"]
            widths = (57, 21, 92)
            caption = "Рисунок 1 — Логическая структура данных каталога"
        else:
            values = ["Браузер\nФормы", "→", "FastAPI\nHTML / API", "→", "catalog.py\nОперации", "→", "SQLAlchemy\nSession", "→", "SQLite\nДанные"]
            widths = (28, 7.5, 28, 7.5, 28, 7.5, 28, 7.5, 28)
            caption = "Рисунок 2 — Обработка запроса в приложении"
        drawing = document.add_table(rows=1, cols=len(values))
        drawing.autofit = False
        for column, width in zip(drawing.columns, widths): column.width = Mm(width)
        for index, (cell, value, width) in enumerate(zip(drawing.rows[0].cells, values, widths)):
            cell.width = Mm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = value
            if index % 2 == 0:
                properties = cell._tc.get_or_add_tcPr()
                borders = OxmlElement("w:tcBorders")
                for side in ("top", "left", "bottom", "right"):
                    edge = OxmlElement("w:" + side)
                    edge.set(qn("w:val"), "single"); edge.set(qn("w:sz"), "6")
                    borders.append(edge)
                properties.append(borders)
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.first_line_indent = Mm(0)
                paragraph.paragraph_format.keep_with_next = True
                paragraph.paragraph_format.line_spacing = 1.15
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"; run.font.size = WordPt(12)
        paragraph = document.add_paragraph(caption)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Mm(0)
        paragraph.paragraph_format.keep_with_next = True
        paragraph = document.add_paragraph("Источник: составлено по модели и исходному коду проекта.")
        paragraph.paragraph_format.first_line_indent = Mm(0)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    lines = (DOCS / "coursework" / "DRAFT.md").read_text().splitlines()
    active = False
    for line in lines:
        if line.startswith("## Введение"): active = True
        if line.startswith("## Что осталось"): break
        if not active or not line.strip(): continue
        if line.startswith("<!-- figure:"):
            diagram(line.split(":", 1)[1].split()[0])
        elif line.startswith("## "):
            heading(line[3:].replace(" — рабочая основа", ""))
        elif line.startswith("### "):
            heading(line[4:], 2)
        elif not line.startswith(("Этот фрагмент введения", "Иллюстрации для этого параграфа:")):
            document.add_paragraph(plain(line))
            if line.startswith("Для курсовой выбран самостоятельный веб-модуль"):
                table("Таблица 1 — Проектное сравнение подходов", ("Подход", "Что организуется", "Соответствие задаче"), [
                    ("Таблица товаров", "Столбцы свойств, правила ввода и связи нужно настроить", "Подходит для исходного перечня; HTTP-модуль не реализует"),
                    ("Готовая система", "Выбор продукта, настройка или расширение", "Возможный прикладной путь; самостоятельная разработка не показана"),
                    ("Отдельный модуль", "Собственные схема, операции, формы и проверки", "Выбран для изучения Python и FastAPI"),
                ], (35, 65, 70))
            elif line.startswith("Поиск сочетается"):
                table("Таблица 2 — Связь требований с проверками", ("Требование", "Реализация", "Признак корректности"), [
                    ("CRUD товара", "Форма, карточка, API", "Изменения видны после чтения; ID сохраняется"),
                    ("Категории", "Справочник и связь", "Повторное имя и удаление занятой категории отклоняются"),
                    ("Поиск", "Нормализованное имя", "Русский регистр не меняет результат"),
                    ("Фильтры", "Условия общего запроса", "Категория, цена и наличие применяются вместе"),
                    ("Пагинация", "LIMIT 10 и OFFSET", "120 страниц для 1200 товаров"),
                    ("Неправильный ввод", "Схемы и форма", "Статус 422; заполненные значения сохранены"),
                    ("Данные после старта", "Файловая SQLite", "Повторное открытие не удаляет записи"),
                ], (36, 54, 80))
            elif line.startswith("Для поиска используется"):
                table("Таблица 3 — Основные поля модели данных", ("Сущность и поле", "Представление", "Правило"), [
                    ("Category.id", "Целое", "Первичный ключ"),
                    ("Category.name", "Строка до 100 символов", "Непустое; уникальна нормализованная форма"),
                    ("Category.description", "Текст или NULL", "Не более 2000 символов"),
                    ("Product.id", "Целое", "Первичный ключ"),
                    ("Product.name", "Строка до 200 символов", "Непустое; нормализованная копия для поиска"),
                    ("Product.sku", "Строка до 64 символов", "Уникальный; латинские буквы, цифры, дефис, подчёркивание"),
                    ("Product.category_id", "Целое", "Внешний ключ; категория существует; RESTRICT"),
                    ("Product.price_kopecks", "Целые копейки", "От 0 до 2^63 − 1; при вводе рубли строкой"),
                    ("Product.quantity", "Целое количество", "От 0 до 2^63 − 1"),
                    ("Product.description", "Текст или NULL", "Не более 2000 символов"),
                    ("Product.created_at, updated_at", "Дата и время", "Хранятся в UTC; обновление при изменении"),
                ], (52, 48, 70))
                document.add_paragraph("Связь таблиц: categories.id → products.category_id, один ко многим. Удаление занятой категории запрещено. Нормализованные поля служебные и не входят в публичную схему API.")
            elif line.startswith("Компоненты организованы"):
                table("Таблица 4 — Ответственность компонентов", ("Компонент", "Назначение"), [
                    ("database.py", "Движок, внешний ключ, сессия на запрос"),
                    ("models.py / schemas.py", "Таблицы, ограничения и проверка входных данных"),
                    ("catalog.py", "Общие операции, транзакции, поиск и фильтры"),
                    ("routers/api.py", "JSON-контракт и статусы HTTP"),
                    ("routers/pages.py", "HTML-формы, сообщения и перенаправления"),
                    ("templates / static", "Представление, оформление и местное время"),
                    ("demo_data.py / seed_demo.py", "Воспроизводимые примеры, backup и загрузка"),
                ], (65, 105))
            elif line.startswith("На этом наборе в Chromium"):
                table("Таблица 5 — Фактические результаты проверки", ("Набор", "Количество", "Результат"), [
                    ("База данных", "35 тестов", "Пройдены"),
                    ("JSON API", "81 тест", "Пройдены"),
                    ("HTML-страницы", "31 тест", "Пройдены"),
                    ("Загрузчик примеров", "7 тестов", "Пройдены"),
                    ("Браузер, основные сценарии", "14 сценариев", "Пройдены в Chromium"),
                    ("Браузер, 1200 товаров", "6 сценариев", "Пройдены в Chromium"),
                    ("SQLite большого набора", "integrity_check, foreign_key_check", "ok; ошибок связей нет"),
                ], (67, 45, 58))

    heading("Список использованных источников")
    sources = json.loads((DOCS / "coursework" / "bibliography.json").read_text())["sources"]
    for source in sources:
        paragraph = document.add_paragraph(f"{source['id']}. {source['description']}")
        paragraph.paragraph_format.first_line_indent = Mm(0)
        paragraph.paragraph_format.space_after = WordPt(6)
    heading("Приложение А. Экраны и результаты демонстрации")
    images = [
        ("large-catalog/04-catalog-viewport.png", "А.1", "Каталог из 1200 демонстрационных товаров"),
        ("03-product-form.png", "А.2", "Форма редактирования товара"),
        ("04-validation.png", "А.3", "Сохранение ввода при неправильной цене"),
        ("07-category-protection.png", "А.4", "Запрет удаления категории с товарами"),
    ]
    for index, (filename, number, caption) in enumerate(images):
        if index: document.add_page_break()
        paragraph = document.add_paragraph(); paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Mm(0)
        paragraph.add_run().add_picture(str(DOCS / "figures" / filename), width=Mm(150))
        paragraph = document.add_paragraph(f"Рисунок {number} — {caption}")
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Mm(0)
        document.add_paragraph("Источник: снимок приложения при браузерной проверке 21.10.2026.")
    # Ссылки на закладки сохраняют номера страниц при обновлении полей Word.
    for title, bookmark, level in headings:
        paragraph = toc_anchor.insert_paragraph_before()
        paragraph.paragraph_format.first_line_indent = Mm(0)
        paragraph.paragraph_format.left_indent = Mm(5) if level == 2 else Mm(0)
        paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.tab_stops.add_tab_stop(Mm(160), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        paragraph.add_run(title + "\t")
        field(paragraph, f" PAGEREF {bookmark} \\h ", "?")
    update = OxmlElement("w:updateFields"); update.set(qn("w:val"), "true")
    document.settings.element.append(update)
    document.core_properties.title = STUDENT["topic"]
    document.core_properties.author = STUDENT["student_name"]
    document.core_properties.last_modified_by = "Сборка проекта"
    document.core_properties.created = document.core_properties.modified = datetime.now(timezone.utc)
    document.core_properties.subject = "Курсовая работа; Разработка программных модулей; 09.02.07"
    document.save(WORD_FILE)
    return WORD_FILE


def make_slides():
    from scripts.build_presentation import build

    return build()


if __name__ == "__main__":
    print(make_word())
    print(make_slides())
