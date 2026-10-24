# Библиография и проверка источников

Список содержит **20 записей**: 8 учебных книг и открытых электронных книг, 9 документов разработчиков, 2 стандарта (ГОСТ и RFC) и методические указания МФЮА. Сквозные ссылки `[1]`–`[20]` использованы в тексте записки. Проверка выполнена 21.10.2026.

Общий минимум новой методички — 15 источников — выполнен. Рекомендация документа об антиплагиате о 15–20 научных источниках относится к составу литературы: в текущем списке есть учебники, стандарты и документация, поэтому число научных публикаций следует оценивать отдельно. Список смешанный, поскольку выданное задание прямо называет официальную документацию Python, PostgreSQL и средств разработки. Долю учебной литературы и документации следует проверить с руководителем при просмотре работы.

Для записки проверялись выбранные главы книг, перечисленные в таблице ниже. Сведения об авторах, издании и ISBN сверены по авторским репозиториям, copyright-страницам и файлам цитирования. Для третьего издания книги Персиваля использована copyright-страница 2025 года: CITATION.md этого репозитория содержит старую запись 2014 года. У электронной версии книги Уилсона не подтверждены год и ISBN печатного издания; в описании эти сведения опущены.

Две книги 2020 года используются как фундаментальные работы о разделении ответственности и регрессионных проверках. Они не служат источником сведений о текущих версиях пакетов. Остальные подтверждённые годы учебных изданий — 2021, 2024 и 2025; для документации указан проверенный адрес и дата обращения, а не вымышленный год публикации.

Библиографические записи подготовлены по модели ГОСТ 7.0.100-2018 с учётом доступных сведений. Неподтверждённые места издания, объём в страницах и DOI не добавлены. Поскольку прочитанные версии доступны как непагинированные электронные тексты, в ссылках используются номера источников, а при необходимости — главы и пункт RFC. Пагинация печатных изданий не использована.

При проверке 21.10.2026 все 18 сетевых адресов из списка вернули HTTP 200; два источника предоставлены пользователем. Некоторые издательские сайты и сайты документации недоступны из облачной сети, поэтому прочитаны официальные GitHub-версии авторов и разработчиков. В [sources-verified.json](sources-verified.json) записаны адреса, размеры, хеши и особенности проверки. Полные тексты книг в репозиторий не копируются.

**Предел проверки ГОСТ 19.201–78:** обозначение и краткое название проверены по выданному заданию. Полный текст стандарта в этой среде не получен. В записке он назван как документ из задания; ссылки на его конкретные пункты и заявление о полном соответствии ТЗ этому стандарту не сделаны. Методические указания МФЮА прочитаны по предоставленному документу.

## Использование в записке

| № | Источник | Какие положения использованы |
|---|---|---|
| 1 | ГОСТ 19.201–78. Единая система программной документации. Техническое задание. | Нормативное обозначение, прямо названное в задании; без пересказа непроверенных пунктов |
| 2 | Московский финансово-юридический университет МФЮА. Методические указания по подготовке и оформлению курсовых работ/проектов. | Общие требования; оформление; источники и ссылки |
| 3 | Downey, A. B. Think Python: How to Think Like a Computer Scientist / A. B. Downey. | Preface; Dictionaries; Classes and Functions |
| 4 | Research Software Engineering with Python: Building Software that Makes Research Possible / D. Irving, K. Hertweck, L. Johnston [et al.]. | Testing Software; Documenting Programs; Tracking Provenance |
| 5 | Percival, H. Architecture Patterns with Python / H. Percival, B. Gregory. | Service Layer: разделение business logic и interfacing code; Unit of Work: atomic operations |
| 6 | Percival, H. J. W. Test-Driven Development with Python / H. J. W. Percival. | What Are We Doing with All These Tests?; Preface: distinction between functional and unit checks |
| 7 | Wilson, G. Software Design by Example: A Tool-Based Introduction with Python / G. Wilson. | Introduction; Object Persistence; A Database; Running Tests |
| 8 | Winters, T. Software Engineering at Google: Lessons Learned from Programming Over Time / T. Winters, T. Manshreck, H. Wright. | Testing Overview: автоматическая проверка и поддержка изменений |
| 9 | Zeller, A. The Debugging Book / A. Zeller. | Introduction to Debugging: систематическое воспроизведение и исправление отказа |
| 10 | The Fuzzing Book / A. Zeller, R. Gopinath, M. Böhme [et al.]. | Introduction to Software Testing: ожидание, проверка, границы достаточности тестов |
| 11 | Python Software Foundation. Python 3.12 Documentation: sqlite3, decimal, unicodedata. | sqlite3: introduction, backup; decimal: exact decimal representation; unicodedata: normalize, NFKC |
| 12 | PostgreSQL Global Development Group. PostgreSQL 18 Documentation: Data Definition. | Table Basics; Constraints; Overview of PostgreSQL Internals: The Path of a Query |
| 13 | FastAPI. Templates: официальная документация. | Using Jinja2Templates; Templates and static files |
| 14 | SQLAlchemy. Session Basics: официальная документация. | What does the Session do?; commit and rollback |
| 15 | Jinja. Template Designer Documentation. | HTML Escaping; Working with Automatic Escaping |
| 16 | Pydantic. Strict Mode: официальная документация. | At the field level; Field(strict=True) |
| 17 | pytest. How to Use Fixtures: официальная документация. | Requesting fixtures; yield fixtures and teardown |
| 18 | Fielding, R. HTTP Semantics / R. Fielding, M. Nottingham, J. Reschke. | HTTP methods; 303 See Other, § 15.4.4 |
| 19 | Microsoft. Playwright for Python: Getting Started | Synchronous API; browser launch, page, browser contexts |
| 20 | Uvicorn. Settings: официальная документация. | Application; Socket Binding; Development |

## Список использованных источников

1. ГОСТ 19.201–78. Единая система программной документации. Техническое задание.

2. Московский финансово-юридический университет МФЮА. Методические указания по подготовке и оформлению курсовых работ/проектов. — Москва, 2025. — Текст : электронный.

3. Downey, A. B. Think Python: How to Think Like a Computer Scientist / A. B. Downey. — 3rd ed. — O’Reilly Media, 2024. — ISBN 978-1-098-15543-8. — URL: https://github.com/AllenDowney/ThinkPython/tree/v3 (дата обращения: 21.10.2026). — Текст : электронный.

4. Research Software Engineering with Python: Building Software that Makes Research Possible / D. Irving, K. Hertweck, L. Johnston [et al.]. — Chapman & Hall/CRC Press, 2021. — ISBN 978-0-367-69834-8. — URL: https://github.com/merely-useful/py-rse (дата обращения: 21.10.2026). — Текст : электронный.

5. Percival, H. Architecture Patterns with Python / H. Percival, B. Gregory. — O’Reilly Media, 2020. — ISBN 978-1-492-05220-3. — URL: https://github.com/cosmicpython/book (дата обращения: 21.10.2026). — Текст : электронный.

6. Percival, H. J. W. Test-Driven Development with Python / H. J. W. Percival. — 3rd ed. — O’Reilly Media, 2025. — ISBN 978-1-098-14871-3. — URL: https://github.com/hjwp/Book-TDD-Web-Dev-Python (дата обращения: 21.10.2026). — Текст : электронный.

7. Wilson, G. Software Design by Example: A Tool-Based Introduction with Python / G. Wilson. — URL: https://github.com/gvwilson/sdxpy (дата обращения: 21.10.2026). — Текст : электронный.

8. Winters, T. Software Engineering at Google: Lessons Learned from Programming Over Time / T. Winters, T. Manshreck, H. Wright. — O’Reilly Media, 2020. — ISBN 978-1-492-08279-8. — URL: https://github.com/abseil/abseil.github.io/blob/master/resources/swe-book/html/ch11.html (дата обращения: 21.10.2026). — Текст : электронный.

9. Zeller, A. The Debugging Book / A. Zeller. — 2021. — URL: https://github.com/uds-se/debuggingbook (дата обращения: 21.10.2026). — Текст : электронный.

10. The Fuzzing Book / A. Zeller, R. Gopinath, M. Böhme [et al.]. — 2021. — URL: https://github.com/uds-se/fuzzingbook (дата обращения: 21.10.2026). — Текст : электронный.

11. Python Software Foundation. Python 3.12 Documentation: sqlite3, decimal, unicodedata. — URL: https://github.com/python/cpython/tree/3.12/Doc/library (дата обращения: 21.10.2026). — Текст : электронный.

12. PostgreSQL Global Development Group. PostgreSQL 18 Documentation: Data Definition. — URL: https://github.com/postgres/postgres/blob/REL_18_STABLE/doc/src/sgml/ddl.sgml (дата обращения: 21.10.2026). — Текст : электронный.

13. FastAPI. Templates: официальная документация. — URL: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/templates.md (дата обращения: 21.10.2026). — Текст : электронный.

14. SQLAlchemy. Session Basics: официальная документация. — URL: https://github.com/sqlalchemy/sqlalchemy/blob/main/doc/build/orm/session_basics.rst (дата обращения: 21.10.2026). — Текст : электронный.

15. Jinja. Template Designer Documentation. — URL: https://github.com/pallets/jinja/blob/main/docs/templates.rst (дата обращения: 21.10.2026). — Текст : электронный.

16. Pydantic. Strict Mode: официальная документация. — URL: https://github.com/pydantic/pydantic/blob/main/docs/concepts/strict_mode.md (дата обращения: 21.10.2026). — Текст : электронный.

17. pytest. How to Use Fixtures: официальная документация. — URL: https://github.com/pytest-dev/pytest/blob/main/doc/en/how-to/fixtures.rst (дата обращения: 21.10.2026). — Текст : электронный.

18. Fielding, R. HTTP Semantics / R. Fielding, M. Nottingham, J. Reschke. — 2022. — RFC 9110. — URL: https://github.com/httpwg/http-core/blob/main/rfc9110.xml (дата обращения: 21.10.2026). — Текст : электронный.

19. Microsoft. Playwright for Python: Getting Started — Library. — URL: https://github.com/microsoft/playwright/blob/main/docs/src/library-python.md (дата обращения: 21.10.2026). — Текст : электронный.

20. Uvicorn. Settings: официальная документация. — URL: https://github.com/encode/uvicorn/blob/main/docs/settings.md (дата обращения: 21.10.2026). — Текст : электронный.
