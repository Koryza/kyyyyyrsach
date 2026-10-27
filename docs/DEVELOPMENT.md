# Среда разработки

Основные команды установки и запуска находятся в [README](../README.md). Нужен Python 3.12.x; версии пакетов закреплены в `requirements.txt` и `requirements-dev.txt`.

## Linux или контейнер

Из корня существующей копии проекта:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-input --disable-pip-version-check --cache-dir /tmp/kyyyyyrsach-pip-cache -r requirements-dev.txt
.venv/bin/python -m pip --cache-dir /tmp/kyyyyyrsach-pip-cache check
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

В подготовленной контейнерной среде копия проекта находится в `/workspace/kyyyyyrsach`. В других системах используйте свой путь. Локальный адрес сервера предназначен для запросов внутри соответствующей машины.

Окружение, кэши и рабочая база не включаются в Git. После восстановления файлов работающий сервер нужно запустить заново. Проверки — в [TESTING.md](TESTING.md).

## Сборка учебных документов

Для Word и PowerPoint нужны дополнительные зависимости:

```bash
.venv/bin/python -m pip install -r requirements-docs.txt
.venv/bin/python -m scripts.build_coursework
```

Сборщик читает `docs/coursework/DRAFT.md`, `bibliography.json`, `student.json` и снимки из `docs/figures/`. Он пересоздаёт DOCX и PPTX; ручные правки этих файлов перед повторной сборкой нужно перенести в исходники либо сохранить отдельно.

PDF экспортируется из Word/LibreOffice и PowerPoint/LibreOffice. После изменения текста обновите поля оглавления и проверьте страницы. Для окончательной записки требуется установленный Times New Roman. В текущем облачном PDF использован Liberation Serif из-за отсутствия этого шрифта.

Отдельный документ с техническими требованиями собирается командой `.venv/bin/python -m scripts.build_requirements` из `docs/requirements/REQUIREMENTS.md`. Она не пересоздаёт записку и презентацию.

## Данные

Обычный сервер использует `data/catalog.db`. Повторный запуск сохраняет записи; `create_all()` создаёт отсутствующие таблицы, но не обновляет существующую схему.

Демонстрационные товары загружаются отдельной командой `python -m scripts.seed_demo`. Перед записью в существующую базу создаётся резервная копия. Порядок загрузки и поведение при повторении описаны в [DEMO_DATA.md](DEMO_DATA.md).
