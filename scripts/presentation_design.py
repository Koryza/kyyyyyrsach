"""Чёрно-белое оформление существующих 15 слайдов без изменения содержимого."""

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from lxml import etree


FONT = "Arial"
BACKGROUND = "FAFAF9"
INK = "171717"
MUTED = "646464"
RULE = "CECECA"


class Layout:
    def __init__(self, slide):
        self.slide = slide
        self.content = {}
        self.placed = set()
        for shape in list(slide.shapes):
            if (shape.has_text_frame and shape.text) or shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                self.content[shape.shape_id - 2] = shape
            else:
                shape._element.getparent().remove(shape._element)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(BACKGROUND)

    def place(self, index, x, y, width, height=None, size=22, bold=False, color=INK, align=PP_ALIGN.LEFT):
        shape = self.content[index]
        self.placed.add(index)
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            height = width * shape.height / shape.width
        shape.left, shape.top = Inches(x), Inches(y)
        shape.width, shape.height = Inches(width), Inches(height)
        if not shape.has_text_frame:
            return shape
        shape.fill.background()
        shape.line.fill.background()
        frame = shape.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = 0
        frame.margin_top = frame.margin_bottom = 0
        frame.vertical_anchor = MSO_ANCHOR.TOP
        for paragraph in frame.paragraphs:
            paragraph.alignment = align
            paragraph.line_spacing = 1.08
            paragraph.space_before = paragraph.space_after = Pt(0)
            for font in [paragraph.font, *(run.font for run in paragraph.runs)]:
                font.name, font.size, font.bold = FONT, Pt(size), bold
                font.color.rgb = RGBColor.from_string(color)
        return shape

    def line(self, x1, y1, x2, y2, color=RULE, weight=.7, arrow=False):
        shape = self.slide.shapes.add_connector(
            MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2),
        )
        shape.line.color.rgb = RGBColor.from_string(color)
        shape.line.width = Pt(weight)
        if arrow:
            end = etree.SubElement(shape._element.spPr.get_or_add_ln(),
                                   "{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd")
            end.set("type", "triangle")
            end.set("w", "sm")
            end.set("len", "sm")
        return shape

    def box(self, x, y, width, height, fill=None, border=RULE):
        shape = self.slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(width), Inches(height),
        )
        if fill:
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor.from_string(fill)
        else:
            shape.fill.background()
        if border:
            shape.line.color.rgb = RGBColor.from_string(border)
            shape.line.width = Pt(.7)
        else:
            shape.line.fill.background()
        return shape

    def header(self, centered=False, size=34):
        self.place(0, .85, .32, 10.8, .24, 10, color=MUTED)
        self.place(1, .85, .78, 11.63, .65, size, True,
                   align=PP_ALIGN.CENTER if centered else PP_ALIGN.LEFT)
        self.line(.85, 6.99, 12.48, 6.99, MUTED)
        self.place(3, .85, 7.17, 9.4, .19, 9.5, color=MUTED)
        self.place(4, 11.38, 7.15, 1.10, .22, 10.5, color=INK, align=PP_ALIGN.RIGHT)

    def finish(self):
        if set(self.content) != self.placed:
            raise ValueError(f"Не размещены блоки: {set(self.content) - self.placed}")


def cover(layout, closing=False):
    layout.place(2, .85, .45, 11.63, .45, 18, color=MUTED)
    layout.place(3, .85, 1.10, 11.63, .25, 11, color=MUTED)
    layout.place(4, .85, 1.72, 11.63, 2.28, 42, True)
    offset = 1 if closing else 0
    if closing:
        layout.place(5, .85, 4.12, 11.63, .55, 25, True)
    layout.place(5 + offset, .85, 5.08, 5.40, .25, 12, color=MUTED)
    layout.place(6 + offset, .85, 5.50, 5.40, .76, 21, True)
    layout.place(7 + offset, .85, 6.35, 5.90, .30, 14, color=MUTED)
    layout.place(8 + offset, 7.18, 5.08, 5.30, .25, 12, color=MUTED)
    layout.place(9 + offset, 7.18, 5.50, 5.30, .76, 21, True)
    layout.line(.85, 6.99, 12.48, 6.99, MUTED)
    layout.place(10 + offset, .85, 7.14, 8.80, .25, 11, color=MUTED)
    layout.place(11 + offset, 11.38, 7.15, 1.10, .22, 10.5, align=PP_ALIGN.RIGHT)


def apply_design(deck):
    """Меняет только геометрию и оформление; текст и исходные PNG остаются прежними."""
    if len(deck.slides) != 15:
        raise ValueError("Оформление рассчитано на текущие 15 слайдов проекта")
    before = [[(shape.shape_id, shape.text) for shape in slide.shapes
               if shape.has_text_frame and shape.text] for slide in deck.slides]
    layouts = [Layout(slide) for slide in deck.slides]
    cover(layouts[0])

    page = layouts[1]
    page.header()
    page.place(5, .85, 2.02, 5.40, 1.40, 76, True)
    page.place(6, .90, 3.48, 5.65, .66, 31, True)
    page.place(8, 7.08, 2.12, 5.40, .28, 11, color=MUTED)
    page.place(9, 7.08, 2.68, 5.40, 1.65, 25)
    for index, x in zip([11, 13, 15], [.85, 4.90, 8.95]):
        page.line(x, 5.12, x + 3.50, 5.12)
        page.place(index, x, 5.35, 3.50, .60, 19)
    page.place(17, .85, 6.30, 11.63, .45, 22, True)

    page = layouts[2]
    page.header()
    page.place(6, .85, 2.08, 4.25, 3.30, 28, True)
    page.place(8, 5.75, 2.02, 6.73, .35, 18, True)
    page.place(9, 5.75, 2.57, 6.73, 1.75, 21)
    page.line(5.75, 4.46, 12.48, 4.46)
    page.place(11, 5.75, 4.72, 6.73, .35, 18, True)
    page.place(12, 5.75, 5.25, 6.73, 1.55, 21)

    page = layouts[3]
    page.header()
    page.place(1, .85, 1.40, 3.45, 1.65, 36, True)
    for name, definition, y in [(7, 8, 1.92), (11, 12, 3.60), (15, 16, 5.28)]:
        page.place(name, 5.02, y, 7.46, .43, 23, True)
        page.place(definition, 5.02, y + .60, 7.46, .90, 21)
    page.line(5.02, 3.42, 12.48, 3.42)
    page.line(5.02, 4.98, 12.48, 4.98)

    page = layouts[4]
    page.header()
    page.box(.85, 1.86, 4.30, 2.38)
    page.box(7.10, 1.86, 5.38, 4.80)
    page.place(7, 1.08, 2.00, 3.84, .35, 18, True)
    page.line(.85, 2.47, 5.15, 2.47)
    for index, y in [(8, 2.67), (9, 3.15), (10, 3.63)]:
        page.place(index, 1.08, y, 3.84, .38, 20)
    page.place(13, 7.35, 2.00, 4.88, .35, 18, True)
    page.line(7.10, 2.47, 12.48, 2.47)
    for offset, index in enumerate(range(14, 23)):
        page.place(index, 7.35, 2.65 + offset * .43, 4.88, .37, 19)
    page.place(24, 5.36, 2.64, 1.53, .40, 23, True, align=PP_ALIGN.CENTER)
    page.line(5.15, 3.25, 7.10, 3.25, INK, 1)
    page.place(25, .85, 4.57, 5.99, .35, 17, True)
    page.place(26, .85, 5.04, 5.99, .28, 13.5, color=MUTED)
    page.place(27, 1.00, 5.46, 4.15, .28, 15, True)
    page.place(28, 5.40, 5.46, 1.42, .28, 14.5, True)
    page.line(.85, 5.82, 6.84, 5.82)
    for name, category, y in [(30, 31, 5.93), (33, 34, 6.25), (36, 37, 6.57)]:
        page.place(name, 1.00, y, 4.15, .29, 15)
        page.place(category, 5.40, y, 1.42, .29, 15)

    page = layouts[5]
    page.header(size=31)
    page.place(5, .85, 1.78, 6.10, .32, 17, True)
    page.place(6, 7.55, 1.78, 4.93, .32, 17, True)
    page.place(7, .85, 2.22, 6.10)
    page.place(8, 7.55, 2.22, 4.93)
    page.place(9, .85, 5.54, 6.10, .42, 22, True)
    page.place(10, .85, 6.03, 6.10, .31, 16, color=MUTED)
    for index, x in zip([12, 15, 18, 21], [.85, 3.90, 6.95, 10.00]):
        page.place(index, x, 6.65, 2.48, .29, 16, align=PP_ALIGN.CENTER)
        if index != 21:
            page.line(x + 2.49, 6.79, x + 2.95, 6.79, INK, .8, arrow=True)

    page = layouts[6]
    page.header(centered=True)
    page.place(5, 1.17, 1.55, 10.99)
    page.place(6, .85, 6.78, 11.63, .18, 9.5, color=MUTED)

    page = layouts[7]
    page.header()
    page.place(1, .85, 1.32, 3.35, 2.00, 35, True)
    page.place(5, 4.45, 2.12, 8.03)
    page.place(7, .85, 3.68, 3.35, 2.25, 23)

    page = layouts[8]
    page.header()
    page.place(5, .85, 1.96, 11.63, .68, 26)
    for name, caption, x in [(7, 8, .85), (11, 12, 4.90), (15, 16, 8.95)]:
        page.line(x, 3.15, x + 3.50, 3.15, INK)
        page.place(name, x, 3.52, 3.50, .55, 27, True)
        page.place(caption, x, 4.25, 3.50, .70, 19)
        if name != 15:
            page.line(x + 3.56, 3.82, x + 3.93, 3.82, INK, .8, arrow=True)
    page.place(17, .85, 5.82, 11.63, .48, 24, True)
    page.place(18, .85, 6.44, 11.63, .30, 14, color=MUTED)

    page = layouts[9]
    page.header(size=32)
    for index, x, width in [(5, .85, 1.67), (6, 2.68, 1.62), (7, 4.48, 1.62)]:
        page.place(index, x, 1.97, width, .30, 15, True)
    for line_y in [2.43, 3.55, 4.65, 5.78]:
        page.line(.85, line_y, 6.15, line_y)
    for indices, y in [([9, 10, 11], 2.69), ([13, 14, 15], 3.79), ([17, 18, 19], 4.89)]:
        for index, x in zip(indices, [.85, 2.68, 4.48]):
            page.place(index, x, y, 1.67, .76, 18, index == indices[0])
    page.place(20, 6.80, 1.94, 5.68, .37, 17, True)
    page.place(21, 6.80, 2.49, 5.68)
    page.place(22, 6.80, 5.72, 5.68, .30, 14, color=MUTED)
    page.place(23, 6.80, 6.13, 4.20)
    page.place(24, .85, 6.08, 5.30, .73, 17)

    page = layouts[10]
    page.header(centered=True)
    page.place(5, .85, 1.97, 4.83, .35, 17, color=MUTED)
    page.place(6, .85, 2.50, 4.83, 1.12, 62, True)
    page.place(7, .85, 4.05, 4.83, .30, 14, color=MUTED)
    page.place(8, .85, 4.51, 4.83, .80, 23, True)
    page.place(9, .85, 5.58, 4.83, .30, 14, color=MUTED)
    page.place(10, .85, 6.03, 4.83, .85, 22, True)
    page.place(11, 6.21, 1.97, 6.27, .36, 17, True)
    page.place(12, 6.21, 2.64, 6.27)
    page.place(13, 6.21, 3.55, 6.27)
    page.place(14, 6.21, 6.10, 6.27, .45, 22)

    page = layouts[11]
    page.header()
    page.place(1, .85, 1.17, 4.40, 1.50, 32, True)
    page.place(5, .85, 2.83, 4.05, .30, 14, color=MUTED)
    page.place(6, .85, 3.27, 4.05, 1.00, 23)
    page.place(7, .85, 4.38, 4.05, 1.12, 60, True)
    page.place(8, .85, 5.60, 4.05, .90, 22, True)
    page.place(9, 5.50, 2.00, 6.98, .37, 17, True)
    page.place(10, 5.50, 2.64, 6.98)
    page.place(11, .85, 6.53, 11.63, .36, 19)

    page = layouts[12]
    page.header()
    page.place(6, .85, 2.15, 3.10, 1.62, 88, True)
    page.place(7, .85, 4.00, 3.10, 1.07, 24)
    page.place(8, .85, 5.55, 3.10, .30, 14, color=MUTED)
    groups = [(9, 12, 2.10), (13, 16, 2.94), (17, 20, 3.78), (21, 24, 4.62)]
    maximum = max(int(page.content[number].text) for _, number, _ in groups)
    for name, number, y in groups:
        count = int(page.content[number].text)
        page.place(name, 4.80, y, 3.00, .40, 21)
        page.box(8.02, y + .18, 3.28, .075, "E1E1DE", None)
        page.box(8.02, y + .18, 3.28 * count / maximum, .075, "4A4A4A", None)
        page.place(number, 11.62, y - .01, .86, .41, 23, True, align=PP_ALIGN.RIGHT)
    page.place(25, 4.80, 5.77, 7.68, .57, 24, True)
    page.place(26, 4.80, 6.44, 7.68, .28, 14, color=MUTED)

    page = layouts[13]
    page.header()
    page.place(5, .85, 1.94, 3.78, .31, 15, True, color=MUTED)
    page.place(6, 4.72, 1.94, 7.76, .31, 15, True, color=MUTED)
    page.line(.85, 2.36, 12.48, 2.36, INK)
    for task, result, y in [(8, 9, 2.56), (11, 12, 3.15), (14, 15, 3.74), (17, 18, 4.33), (20, 21, 4.92), (23, 24, 5.51), (26, 27, 6.10)]:
        page.place(task, .85, y, 3.78, .42, 18, True)
        page.place(result, 4.72, y, 7.76, .42, 18)
        page.line(.85, y + .48, 12.48, y + .48)

    cover(layouts[14], closing=True)
    for layout in layouts:
        layout.finish()
        for shape in layout.slide.shapes:
            properties = getattr(shape._element, "spPr", None)
            if properties is not None:
                for effect in list(properties):
                    if etree.QName(effect).localname in {"effectLst", "effectDag"}:
                        properties.remove(effect)
                properties.append(etree.Element("{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst"))
            effect_ref = shape._element.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}effectRef")
            if effect_ref is not None:
                effect_ref.set("idx", "0")
    after = [[(shape.shape_id, shape.text) for shape in slide.shapes
              if shape.has_text_frame and shape.text] for slide in deck.slides]
    if before != after:
        raise ValueError("При изменении оформления изменился исходный текст")
    return deck
