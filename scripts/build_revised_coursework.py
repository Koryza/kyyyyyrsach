"""Собрать новую редакцию записки, сохранив исходный Word-файл.

python -m scripts.build_revised_coursework [--pages /tmp/heading-pages.json]
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph
from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / 'docs/coursework/revision'
OUTPUT = DIRECTORY / 'Курсовая_новая_редакция.docx'
HEADINGS = [18, 26, 27, 37, 50, 60, 61, 74, 90, 103, 104, 115, 126, 146, 154, 175]


def replace_text(paragraph, value):
    properties = deepcopy(paragraph.runs[0]._r.rPr) if paragraph.runs else None
    paragraph.clear()
    run = paragraph.add_run(value)
    if properties is not None:
        run._r.insert(0, properties)


def write_cell(cell, value, template=None):
    source = (template or cell).paragraphs[0]
    paragraph_properties = deepcopy(source._p.pPr)
    run_properties = deepcopy(source.runs[0]._r.rPr) if source.runs else None
    cell.text = ''
    for index, line in enumerate(value.split('\n')):
        paragraph = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
        if paragraph_properties is not None:
            if paragraph._p.pPr is not None:
                paragraph._p.remove(paragraph._p.pPr)
            paragraph._p.insert(0, deepcopy(paragraph_properties))
        run = paragraph.add_run(line)
        if run_properties is not None:
            run._r.insert(0, deepcopy(run_properties))


def check_evidence():
    automatic = ET.parse(DIRECTORY / 'checks/tests.xml').getroot()
    if len(list(automatic.iter('testcase'))) != 173 or list(automatic.iter('failure')) or list(automatic.iter('error')):
        raise ValueError('Нужен протокол 173 пройденных тестов')
    main = json.loads((DIRECTORY / 'checks/browser-main.json').read_text())
    catalog = json.loads((DIRECTORY / 'checks/browser-catalog.json').read_text())
    if main['checks_passed'] != 14 or catalog['passed'] != 13:
        raise ValueError('Числа браузерных проверок не совпадают с текстом')
    if any(case['expected'] != case['actual'] or not case['passed'] for case in main['product_cases']):
        raise ValueError('Не совпали результаты основных браузерных случаев')
    if any(case['expected'] != case['actual'] or not case['passed'] for case in catalog['checks']):
        raise ValueError('Не совпали результаты проверки каталога')
    if not main['checked_at_utc'].startswith('2026-11-12') or not catalog['timestamp'].startswith('2026-11-12'):
        raise ValueError('Протоколы относятся к другой дате')


def build(page_numbers=None):
    content = json.loads((DIRECTORY / 'content.json').read_text())
    page_numbers = page_numbers or content.get('heading_pages')
    base = ROOT / content['base']
    if hashlib.sha256(base.read_bytes()).hexdigest() != content['base_sha256']:
        raise ValueError('Исходная редакция изменилась: нужно сверить номера абзацев')
    check_evidence()
    document = Document(base)
    paragraphs = list(document.paragraphs)
    original_goal = paragraphs[22].text
    for index, value in content['paragraphs'].items():
        replace_text(paragraphs[int(index)], value)
    for index, values in content['insert_after'].items():
        anchor = paragraphs[int(index)]
        for value in values:
            node = OxmlElement('w:p')
            anchor._p.addnext(node)
            paragraph = Paragraph(node, anchor._parent)
            paragraph.style = document.styles['Normal']
            paragraph.add_run(value)
            anchor = paragraph

    # В логической схеме каждый атрибут показан отдельной строкой.
    model = document.tables[2]
    write_cell(model.cell(0, 2), 'ТОВАР\nid (PK)\nsku (UQ)\ncategory_id (FK)\nname\nname_normalized\ndescription\nprice_kopecks\nquantity\ncreated_at\nupdated_at')
    model.cell(0, 0).vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    model.cell(0, 2).vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP

    fields = document.tables[3]
    field_rows = [
        ('Category.id', 'Целое', 'Первичный ключ'),
        ('Category.name', 'Строка до 100 символов', 'Непустое название'),
        ('Category.name_normalized', 'Нормализованный текст', 'Уникальность без учёта регистра; служебное поле'),
        ('Category.description', 'Текст или NULL', 'Не более 2000 символов'),
        ('Product.id', 'Целое', 'Первичный ключ'),
        ('Product.name', 'Строка до 200 символов', 'Непустое название'),
        ('Product.name_normalized', 'Нормализованный текст', 'Поиск; заполняется вместе с названием'),
        ('Product.sku', 'Строка до 64 символов', 'Уникальный; латинские буквы, цифры, дефис, подчёркивание'),
        ('Product.category_id', 'Целое', 'Внешний ключ; категория существует; RESTRICT'),
        ('Product.price_kopecks', 'Целые копейки', 'От 0 до 2^63 − 1; на входе рубли строкой'),
        ('Product.quantity', 'Целое количество', 'От 0 до 2^63 − 1'),
        ('Product.description', 'Текст или NULL', 'Не более 2000 символов'),
        ('Product.created_at', 'Дата и время UTC', 'Назначается при создании'),
        ('Product.updated_at', 'Дата и время UTC', 'Назначается при создании и изменении'),
    ]
    template = deepcopy(fields.rows[1]._tr)
    for row in list(fields.rows)[1:]:
        fields._tbl.remove(row._tr)
    for values in field_rows:
        fields._tbl.append(deepcopy(template))
        row = fields.rows[-1]
        for cell, value in zip(row.cells, values):
            write_cell(cell, value)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.keep_with_next = False

    components = document.tables[4]
    write_cell(components.cell(3, 1), 'Общие операции, транзакции, поиск, фильтры и итоги')
    template = deepcopy(components.rows[1]._tr)
    components._tbl.append(template)
    components.rows[3]._tr.addnext(template)
    row = components.rows[4]
    write_cell(row.cells[0], 'web.py')
    write_cell(row.cells[1], 'Форматирование, подготовка диаграмм, версии CSS и JavaScript')

    results = document.tables[6]
    write_cell(results.cell(3, 1), '50 тестов')
    write_cell(results.cell(6, 0), 'Браузер, выборка и диаграммы')
    write_cell(results.cell(6, 1), '13 проверок')

    images = ['catalog.png', 'product-form.png', 'invalid-price.png', 'category-protection.png']
    for shape, filename in zip(document.inline_shapes, images, strict=True):
        path = DIRECTORY / 'figures' / filename
        relation = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
        document.part.related_parts[relation]._blob = path.read_bytes()
        with Image.open(path) as image:
            width, height = image.size
        width_cm = min(15, 18 * width / height)
        shape.width, shape.height = Cm(width_cm), Cm(width_cm * height / width)
    for index in [178, 182, 186, 190]:
        replace_text(paragraphs[index], 'Источник: снимок приложения при браузерной проверке 12.11.2026.')

    document.add_page_break()
    image_paragraph = document.add_paragraph()
    image_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    image_paragraph.paragraph_format.first_line_indent = Cm(0)
    image_paragraph.paragraph_format.keep_with_next = True
    image_paragraph.add_run().add_picture(str(DIRECTORY / 'figures/summary.png'), width=Cm(15))
    for text, source in [
        ('Рисунок А.5 — Сводные показатели и диаграммы каталога', paragraphs[189]),
        ('Источник: снимок приложения при браузерной проверке 12.11.2026.', paragraphs[190]),
    ]:
        paragraph = document.add_paragraph()
        properties = deepcopy(source._p.pPr)
        if properties is not None:
            paragraph._p.insert(0, properties)
        paragraph.add_run(text)

    if page_numbers:
        contents = document.element.body.xpath('.//w:sdtContent//w:p')
        contents = [node for node in contents if node.xpath('.//w:t')]
        for toc, heading_index in zip(contents, HEADINGS, strict=True):
            title = paragraphs[heading_index].text
            value = str(page_numbers[title])
            nodes = toc.xpath('.//w:t')
            if not nodes or not nodes[-1].text.isdigit():
                raise ValueError('Не найден номер страницы в содержании')
            nodes[-1].text = value
    settings = document.settings.element
    update_fields = settings.find(qn('w:updateFields'))
    if update_fields is None:
        update_fields = OxmlElement('w:updateFields')
        settings.append(update_fields)
    update_fields.set(qn('w:val'), 'true')
    document.core_properties.modified = datetime.now(timezone.utc)
    document.core_properties.last_modified_by = 'Редакция документа'
    if paragraphs[22].text != original_goal:
        raise ValueError('Изменилась цель и задачи, согласованные с презентацией')
    document.save(OUTPUT)
    return OUTPUT


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', type=Path)
    args = parser.parse_args()
    pages = json.loads(args.pages.read_text()) if args.pages else None
    print(build(pages))
