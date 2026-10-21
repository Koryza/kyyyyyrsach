"""Синтетический ассортимент: 12 категорий × 10 типов × 10 вариантов.

Цены и остатки условные. Артикулы стабильны, реальных брендов и поставщиков нет.
"""

from dataclasses import dataclass

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.models import Category, Product, normalize_name
from app.schemas import CategoryWrite, ProductWrite, format_price


@dataclass(frozen=True)
class DemoGroup:
    name: str
    description: str
    types: tuple[str, ...]
    variants: tuple[str, ...]
    base_kopecks: int


COLORS = ("синий", "чёрный", "красный", "зелёный", "фиолетовый")
GROUPS = (
    DemoGroup("Письменные принадлежности", "Ручки и инструменты для повседневных записей.",
        ("Ручка шариковая", "Ручка гелевая", "Ручка капиллярная", "Ручка автоматическая",
         "Ручка масляная", "Ручка со стилусом", "Ручка с грипом", "Ручка для левшей",
         "Стержень шариковый", "Стержень гелевый"),
        tuple(f"цвет {color}, линия {line} мм" for color in COLORS for line in ("0,5", "0,7")), 2990),
    DemoGroup("Бумага и бумажная продукция", "Бумага для печати, черчения и оформления.",
        ("Бумага офисная", "Бумага цветная", "Бумага для черчения", "Бумага самоклеящаяся",
         "Бумага для заметок", "Бумага дизайнерская", "Бумага для принтера", "Бумага матовая",
         "Бумага мелованная", "Бумага для оригами"),
        tuple(f"формат {size}, {sheets} листов" for size in ("А4", "А5") for sheets in (20, 50, 100, 250, 500)), 7900),
    DemoGroup("Тетради и блокноты", "Тетради, ежедневники и записные книжки.",
        ("Тетрадь в клетку", "Тетрадь в линейку", "Тетрадь общая", "Блокнот на пружине",
         "Блокнот в точку", "Записная книжка", "Ежедневник недатированный", "Скетчбук",
         "Тетрадь на кольцах", "Планер настольный"),
        tuple(f"{sheets} листов, обложка {cover}" for sheets in (24, 48, 60, 80, 96) for cover in ("мягкая", "твёрдая")), 4900),
    DemoGroup("Папки и файлы", "Хранение и перенос текущих документов.",
        ("Папка на кнопке", "Папка на молнии", "Папка-уголок", "Папка с зажимом",
         "Папка с кольцами", "Папка с файлами", "Папка на резинках", "Папка с завязками",
         "Папка-планшет", "Папка-конверт"),
        tuple(f"{size}, цвет {color}" for size in ("А4", "А5") for color in COLORS), 5900),
    DemoGroup("Архивирование документов", "Коробки, разделители и принадлежности архива.",
        ("Короб архивный", "Папка архивная", "Лоток архивный", "Папка-регистратор",
         "Короб для документов", "Папка для подшивки", "Накопитель вертикальный",
         "Разделитель архивный", "Обложка архивная", "Папка с арочным механизмом"),
        tuple(f"серия {series}, корешок {width} мм" for series in ("Стандарт", "Усиленная") for width in (30, 40, 50, 70, 80)), 12900),
    DemoGroup("Настольные принадлежности", "Организация рабочего места менеджера.",
        ("Подставка для ручек", "Органайзер настольный", "Лоток горизонтальный",
         "Лоток вертикальный", "Подставка для бумаг", "Подставка для визиток",
         "Подставка для телефона", "Держатель для заметок", "Контейнер для мелочей",
         "Набор настольный"),
        tuple(f"цвет {color}, размер {size}" for color in COLORS for size in ("компактный", "стандартный")), 14900),
    DemoGroup("Карандаши и ластики", "Карандаши, ластики и принадлежности для заточки.",
        ("Карандаш графитный HB", "Карандаш графитный 2B", "Карандаш механический",
         "Набор цветных карандашей", "Ластик белый", "Ластик комбинированный",
         "Точилка с контейнером", "Точилка металлическая", "Ластик в держателе",
         "Набор карандаш и ластик"),
        tuple(f"серия {series}, упаковка {count} шт." for series in ("Учебная", "Офисная") for count in (1, 2, 3, 5, 10)), 1900),
    DemoGroup("Рисование и творчество", "Материалы для рисунка и учебных проектов.",
        ("Набор акварели", "Набор гуаши", "Набор акриловых красок", "Набор пастели",
         "Набор фломастеров", "Набор восковых мелков", "Набор кистей", "Набор цветного картона",
         "Набор цветной бумаги", "Набор для аппликаций"),
        tuple(f"{count} элементов, серия {series}" for count in (6, 8, 12, 18, 24) for series in ("Базовая", "Расширенная")), 9900),
    DemoGroup("Клей и клейкие ленты", "Клеевые материалы для бумаги и упаковки.",
        ("Клей-карандаш", "Клей ПВА", "Клей канцелярский", "Клей для картона",
         "Лента канцелярская", "Лента двусторонняя", "Лента упаковочная", "Лента малярная",
         "Клеевые подушечки", "Клеевые полоски"),
        tuple(f"серия {series}, упаковка {count} шт." for series in ("Стандарт", "Усиленная") for count in (1, 2, 3, 5, 10)), 3900),
    DemoGroup("Степлеры и скрепление", "Инструменты и расходные материалы для скрепления.",
        ("Степлер компактный", "Степлер настольный", "Степлер усиленный", "Антистеплер",
         "Дырокол компактный", "Дырокол настольный", "Набор скоб", "Набор скрепок",
         "Набор зажимов", "Набор канцелярских кнопок"),
        tuple(f"серия {series}, комплект {count} шт." for series in ("Офис", "Учёба") for count in (1, 2, 3, 5, 10)), 6900),
    DemoGroup("Маркеры и выделители", "Маркеры для бумаги, досок и презентаций.",
        ("Маркер перманентный", "Маркер для доски", "Маркер для флипчарта",
         "Маркер текстовый", "Маркер двусторонний", "Маркер акварельный",
         "Маркер для дисков", "Маркер тонкий", "Выделитель пастельный", "Выделитель неоновый"),
        tuple(f"цвет {color}, наконечник {tip}" for color in COLORS for tip in ("тонкий", "скошенный")), 4590),
    DemoGroup("Упаковка и маркировка", "Конверты, пакеты и этикетки для документов.",
        ("Конверт бумажный", "Конверт картонный", "Конверт с окном", "Пакет почтовый",
         "Пакет для документов", "Пакет подарочный", "Набор этикеток", "Набор бирок",
         "Набор наклеек", "Пакет крафтовый"),
        tuple(f"серия {series}, упаковка {count} шт." for series in ("Стандарт", "Плотная") for count in (5, 10, 20, 50, 100)), 3500),
)
DEMO_PRODUCT_COUNT = sum(len(group.types) * len(group.variants) for group in GROUPS)


@dataclass(frozen=True)
class SeedResult:
    categories_added: int
    products_added: int
    products_skipped: int


def seed_catalog(db_engine: Engine) -> SeedResult:
    """Добавить недостающее одной транзакцией; совпавшие артикулы не изменять.

    Таблицы должны быть созданы вызывающим кодом. Ошибка откатывает всю загрузку.
    """
    added_categories = added_products = skipped_products = 0
    with Session(db_engine) as session, session.begin():
        categories = {item.name_normalized: item for item in session.scalars(select(Category))}
        existing_skus = set(session.scalars(select(Product.sku)))
        for group_number, group in enumerate(GROUPS, start=1):
            category = categories.get(normalize_name(group.name))
            # Не создавать новую категорию, если все её DEMO-артикулы уже есть.
            missing = [
                (type_number, product_type, variant_number, variant,
                 f"DEMO-{group_number:02d}-{type_number:02d}-{variant_number:02d}")
                for type_number, product_type in enumerate(group.types, start=1)
                for variant_number, variant in enumerate(group.variants, start=1)
                if f"DEMO-{group_number:02d}-{type_number:02d}-{variant_number:02d}" not in existing_skus
            ]
            skipped_products += len(group.types) * len(group.variants) - len(missing)
            if not missing:
                continue
            if category is None:
                data = CategoryWrite(name=group.name, description=group.description)
                category = Category(name=data.name, description=data.description)
                session.add(category)
                session.flush()  # Получить ID для строгой схемы ProductWrite.
                categories[category.name_normalized] = category
                added_categories += 1
            for type_number, product_type, variant_number, variant, sku in missing:
                ordinal = (group_number - 1) * 100 + (type_number - 1) * 10 + variant_number
                price = group.base_kopecks + (type_number - 1) * 1700 + (variant_number - 1) * 490
                quantity = 0 if ordinal % 9 == 0 else 1 + (ordinal * 37) % 150
                data = ProductWrite(
                    name=f"{product_type} — {variant}", sku=sku, category_id=category.id,
                    description=f"{group.description} {product_type}; {variant}. "
                                "Демонстрационный товар. Цена и остаток условные.",
                    price=format_price(price), quantity=quantity,
                )
                session.add(Product(
                    name=data.name, sku=data.sku, description=data.description,
                    category=category, price_kopecks=data.price_kopecks, quantity=data.quantity,
                ))
                added_products += 1
    return SeedResult(added_categories, added_products, skipped_products)
