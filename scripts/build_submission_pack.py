"""Сборка папки «сдача проекта»: КП, отчёт, скриншоты, PDF."""
from __future__ import annotations

import shutil
import textwrap
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "сдача проекта"
SCREENSHOTS = OUT / "скриншоты"
GITHUB_URL = "https://github.com/Ollegro/rental-ai-assistant-graduation"
BOT_NAME = "Джонни Рентино"
BOT_USERNAME = "@yandworkflow_bot"
BOT_URL = "https://t.me/yandworkflow_bot"
MANAGER_GROUP_URL = "https://t.me/testing_bots77"
COMPANY_PHONE = "+7 903 841 7000"
TODAY = date.today().strftime("%d.%m.%Y")

# Telegram dark theme
BG = (14, 22, 33)
BOT_BUBBLE = (36, 47, 61)
USER_BUBBLE = (43, 82, 120)
TEXT = (255, 255, 255)
MUTED = (113, 132, 153)
BTN_BG = (36, 47, 61)
BTN_TEXT = (110, 181, 246)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        ("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        ("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _wrap(text: str, width: int = 42) -> list[str]:
    return textwrap.wrap(text, width=width) or [""]


def _bubble_height(lines: list[str], font, pad_y: int = 14, line_gap: int = 6) -> int:
    bbox = font.getbbox("Ay")
    line_h = bbox[3] - bbox[1]
    return pad_y * 2 + len(lines) * line_h + max(0, len(lines) - 1) * line_gap


def _draw_bubble(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    lines: list[str],
    *,
    right: bool = False,
    fill=BOT_BUBBLE,
    font=None,
) -> int:
    font = font or _font(20)
    line_gap = 6
    pad_x, pad_y = 16, 14
    bubble_h = _bubble_height(lines, font, pad_y, line_gap)
    bx = x if not right else x - w
    draw.rounded_rectangle((bx, y, bx + w, y + bubble_h), radius=18, fill=fill)
    ty = y + pad_y
    bbox = font.getbbox("Ay")
    line_h = bbox[3] - bbox[1]
    for line in lines:
        draw.text((bx + pad_x, ty), line, fill=TEXT, font=font)
        ty += line_h + line_gap
    return bubble_h


def _draw_buttons(draw: ImageDraw.ImageDraw, y: int, labels: list[str], width: int = 520) -> int:
    font = _font(18)
    x = 40
    cur_y = y
    for label in labels:
        bbox = font.getbbox(label)
        h = bbox[3] - bbox[1] + 24
        draw.rounded_rectangle((x, cur_y, x + width, cur_y + h), radius=10, fill=BTN_BG)
        draw.text((x + 16, cur_y + 12), label, fill=BTN_TEXT, font=font)
        cur_y += h + 8
    return cur_y - y


def make_chat_screenshot(
    path: Path,
    *,
    title: str,
    messages: list[tuple[str, bool]],
    buttons: list[str] | None = None,
    height: int = 900,
) -> None:
    img = Image.new("RGB", (600, height), BG)
    draw = ImageDraw.Draw(img)
    title_font = _font(22, bold=True)
    draw.text((24, 18), title, fill=TEXT, font=title_font)
    draw.text((24, 48), BOT_USERNAME, fill=MUTED, font=_font(14))

    y = 90
    msg_font = _font(19)
    for text, is_user in messages:
        lines = _wrap(text, 38 if is_user else 40)
        bubble_w = min(480, max(120, max(len(l) for l in lines) * 11 + 32))
        h = _draw_bubble(
            draw,
            560 if is_user else 40,
            y,
            bubble_w,
            lines,
            right=is_user,
            fill=USER_BUBBLE if is_user else BOT_BUBBLE,
            font=msg_font,
        )
        y += h + 14

    if buttons:
        y += 8
        _draw_buttons(draw, y, buttons)

    img.save(path, "PNG", optimize=True)


def make_house_card_screenshot(path: Path) -> None:
    photo_path = ROOT / "data" / "photos" / "house-008" / "01.jpg"
    photo = Image.open(photo_path).convert("RGB")
    photo = photo.resize((560, 360))

    height = 980
    img = Image.new("RGB", (600, height), BG)
    img.paste(photo, (20, 70))
    draw = ImageDraw.Draw(img)
    draw.text((24, 18), BOT_NAME, fill=TEXT, font=_font(22, bold=True))
    draw.text((24, 48), BOT_USERNAME, fill=MUTED, font=_font(14))

    caption = (
        "🏡 Семейный дом у пляжа #8 (house-008)\n"
        "Евпатория · 4–6 гостей · от 95 000 ₽/мес\n"
        "Парковка, Wi‑Fi, бильярд, офис"
    )
    y = 450
    for line in caption.split("\n"):
        draw.text((28, y), line, fill=TEXT, font=_font(18))
        y += 28

    buttons = [
        "✨ Оформить заявку — perfetto!",
        "🏠 Подобрать casa    📞 Перезвоните мне",
        f"☎️ {COMPANY_PHONE} — скопировать",
    ]
    _draw_buttons(draw, 560, buttons)
    img.save(path, "PNG", optimize=True)


def write_kp_markdown(path: Path) -> None:
    path.write_text(
        f"""# Коммерческое предложение
## ИИ-ассистент «{BOT_NAME}» для компании по аренде домов

**Дата:** {TODAY}  
**Заказчик:** компания загородной аренды (B2C)  
**Исполнитель:** выпускной проект Zerocoder · Prompt Engineering

---

## 1. Описание проекта

### 1.1. Цель проекта

Разработка Telegram-бота с RAG-системой для автоматизации консультаций клиентов по аренде загородных домов: ответы на вопросы об объектах, подбор по критериям, приём заявок и заказ обратного звонка с уведомлением менеджеров.

### 1.2. Используемые технологии

| Компонент | Технология |
|-----------|------------|
| Интерфейс | Telegram Bot API, python-telegram-bot |
| Логика | Python 3.12 |
| RAG | LangChain + FAISS |
| LLM | OpenAI API (gpt-4o-mini) / ProxyAPI |
| Данные | JSON (50 объектов), фото объектов |
| Деплой | Beget VPS, systemd |

### 1.3. Среда развёртывания

- Сервер Linux (VPS Beget), сервис `rental-bot` 24/7
- Векторный индекс FAISS на сервере
- Секреты в `.env` (BOT_TOKEN, API_KEY)

---

## 2. Основные функции бота

### 2.1. Функциональные требования

**Консультации (RAG):**
- ответы на вопросы о домах, ценах, условиях аренды;
- только факты из базы знаний, без «галлюцинаций»;
- персонализация: сеньор / сеньорита, имя клиента.

**Подбор домов:**
- фильтры: регион, число гостей, бюджет;
- карточка объекта с фото и inline-кнопками.

**Заявки:**
- с карточки дома: телефон → время звонка → сообщение;
- валидация номера (+7 / 7 / 8);
- уведомление менеджерам в Telegram-группу.

**Обратный звонок:**
- сценарий: телефон → удобное время → описание ситуации.

**Дополнительно:**
- персона «{BOT_NAME}» (итальянский стиль общения);
- подарок клиенту — ссылка на музыкальный альбом Suno после заявки.

### 2.2. Архитектура

```
Telegram → bot.py → rag.py (FAISS + LangChain + LLM)
                      ↑
              data/properties.json + photos
```

---

## 3. Реализация проекта

### 3.1. База знаний
- 50 объектов недвижимости в `properties.json`
- фото для карточек домов
- системный промпт в `prompts/system.txt`

### 3.2. RAG-ассистент
- построение FAISS-индекса (`build_index.py`)
- retrieval + генерация ответа LLM

### 3.3. Telegram-бот
- онбординг, inline-меню, диалоги заявок
- деплой: `python deploy_bot.py`

---

## 4. Внедрение и передача

- бот развёрнут на VPS и работает в режиме polling;
- заявки сохраняются в `applications.json`;
- менеджеры получают уведомления в группу;
- исходный код: {GITHUB_URL}

**Демо:**
- Telegram-бот: {BOT_URL} ({BOT_USERNAME})
- Группа заявок менеджеров: {MANAGER_GROUP_URL}

---

## 5. Сроки, стоимость и условия

| Параметр | Значение |
|----------|----------|
| Срок разработки MVP | 2 недели (по ТЗ курса) |
| Стоимость (учебный проект) | по договорённости с заказчиком |
| Поддержка | доработки по отдельному соглашению |

---

## 6. Аналогичный кейс — скриншоты

См. папку `скриншоты/` в комплекте сдачи:

1. Приветствие и главное меню  
2. Подбор дома (фильтры)  
3. Карточка дома с фото  
4. RAG-консультация  
5. Оформление заявки  
6. Подтверждение и подарок  

**GitHub:** {GITHUB_URL}  
**Бот:** {BOT_URL}  
**Группа заявок:** {MANAGER_GROUP_URL}
""",
        encoding="utf-8",
    )


def write_report(path: Path) -> None:
    path.write_text(
        f"""ОТЧЁТ О ВЫПОЛНЕНИИ ВЫПУСКНОГО ПРОЕКТА
Zerocoder · Prompt Engineering
Дата: {TODAY}

Тема: ИИ-система для компании, предоставляющей дома в аренду.

---

ЧТО РЕАЛИЗОВАНО

1. RAG-ассистент на базе LangChain + FAISS + LLM API (gpt-4o-mini).
   База знаний: 50 объектов недвижимости в data/properties.json.

2. Telegram-бот «{BOT_NAME}»:
   - консультации в свободной форме (ответы только по базе знаний);
   - подбор домов: регион → гости → бюджет → карточки с фото;
   - заявка с карточки: телефон (с валидацией) → время звонка → сообщение;
   - заказ обратного звонка с уведомлением менеджеров в группу;
   - inline-меню, персонализация (сеньор/сеньорита), подарок Suno после заявки.

3. Промпт-инжиниринг: системный промпт prompts/system.txt с ролью консультанта,
   правилами работы с контекстом и стилем персонажа.

4. Деплой на VPS Beget (systemd rental-bot), скрипт deploy_bot.py.

5. Репозиторий GitHub: {GITHUB_URL}
6. Telegram-бот: {BOT_URL}
7. Группа заявок: {MANAGER_GROUP_URL}

---

ЧТО НЕ РЕАЛИЗОВАНО / ОГРАНИЧЕНИЯ

- n8n / Albato не использовались — вся логика на Python (допустимо по ТЗ).
- CRM не интегрирована — заявки в JSON + Telegram-группа менеджеров.

---

ПЛАНЫ РАЗВИТИЯ

- интеграция с AmoCRM / Bitrix24;
- админ-панель заявок;
- оплата бронирования;
- мультиязычность (IT/RU).

---

ПРОВЕРКА

- /start → меню → подбор дома → заявка → подтверждение
- свободный вопрос «дом у моря до 100000» → RAG-ответ
- GitHub: {GITHUB_URL}
""",
        encoding="utf-8",
    )


def write_portfolio(path: Path) -> None:
    path.write_text(
        f"""ПОРТФОЛИО · КЕЙС ДЛЯ РЕЗЮМЕ

Название: {BOT_NAME} — ИИ-консультант по аренде домов

Описание:
Telegram-бот с RAG для компании загородной аренды. Автоматизирует консультации,
подбор объектов и приём заявок. Персона бота — итальянский консультант с юмором.

Стек: Python, LangChain, FAISS, OpenAI API, Telegram Bot API, VPS/Linux.

Результат:
- 50 объектов в базе знаний, векторный поиск
- сценарии заявок и обратного звонка
- деплой 24/7 на VPS

Ссылки:
- GitHub: {GITHUB_URL}
- Telegram-бот: {BOT_URL} ({BOT_USERNAME})
- Группа заявок: {MANAGER_GROUP_URL}

Навыки для резюме:
Prompt Engineering · RAG · LangChain · FAISS · Python · Telegram Bots · LLM API · VPS deploy
""",
        encoding="utf-8",
    )


def write_readme(path: Path) -> None:
    path.write_text(
        f"""# Сдача выпускного проекта Zerocoder

Комплект материалов для загрузки на платформу university.zerocoder.ru

## Что приложить к домашнему заданию

| № | Файл | Куда |
|---|------|------|
| 1 | `коммерческое-предложение/КП-Джонни-Рентино.pdf` | файл КП |
| 2 | `отчёт/отчёт-для-платформы.txt` | текст в поле сдачи |
| 3 | {GITHUB_URL} | GitHub |
|   | {BOT_URL} | бот {BOT_USERNAME} |
|   | {MANAGER_GROUP_URL} | группа заявок |
| 4 | `портфолио/описание-проекта-для-резюме.md` + ваше резюме | файлы |
| 5 | `образец/КП. Пример. ТГ-бот.pdf` | образец Zerocoder (для себя) |

## Скриншоты

Папка `скриншоты/` — для раздела «Аналогичный кейс» в КП.

## Быстрая проверка бота перед сдачей

1. /start
2. 🏠 Подобрать casa
3. ✨ Оформить заявку на карточке дома
4. Вопрос в чат про дом у моря
""",
        encoding="utf-8",
    )


def build_kp_pdf(pdf_path: Path, shots_dir: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        Image as RlImage,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    font_reg = Path(r"C:\Windows\Fonts\arial.ttf")
    font_bold = Path(r"C:\Windows\Fonts\arialbd.ttf")
    if not font_reg.exists():
        raise FileNotFoundError("Не найден Arial — нужен для кириллицы в PDF")
    pdfmetrics.registerFont(TTFont("Arial", str(font_reg)))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(font_bold)))
    pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold")

    styles = {
        "title": ParagraphStyle(
            "title",
            fontName="Arial-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName="Arial",
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#444444"),
            spaceAfter=20,
        ),
        "h1": ParagraphStyle(
            "h1",
            fontName="Arial-Bold",
            fontSize=14,
            leading=18,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#1a5276"),
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName="Arial-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Arial",
            fontSize=11,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName="Arial",
            fontSize=11,
            leading=14,
            leftIndent=14,
            bulletIndent=0,
            spaceAfter=3,
        ),
        "mono": ParagraphStyle(
            "mono",
            fontName="Arial",
            fontSize=10,
            leading=13,
            backColor=colors.HexColor("#f4f6f7"),
            borderPadding=8,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "caption",
            fontName="Arial-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=4,
        ),
    }

    def p(style: str, text: str):
        safe = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return Paragraph(safe, styles[style])

    def bullets(items: list[str]):
        return [p("bullet", f"• {item}") for item in items]

    def table(rows: list[list[str]], col_widths: list[float]):
        data = [[Paragraph(cell, styles["body"]) for cell in row] for row in rows]
        t = Table(data, colWidths=col_widths, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, 0), "Arial-Bold", 11),
                    ("FONT", (0, 1), (-1, -1), "Arial", 10),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d6eaf8")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return t

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"КП — {BOT_NAME}",
        author="Zerocoder Graduation Project",
    )
    w = doc.width
    story: list = []

    # Титул
    story.append(Spacer(1, 1.5 * cm))
    story.append(p("title", "Коммерческое предложение"))
    story.append(p("subtitle", f"ИИ-ассистент «{BOT_NAME}» для компании по аренде домов"))
    story.append(
        table(
            [
                ["Дата", TODAY],
                ["Заказчик", "Компания загородной аренды (B2C)"],
                ["Исполнитель", "Выпускной проект Zerocoder · Prompt Engineering"],
            ],
            [4 * cm, w - 4 * cm],
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    # 1
    story.append(p("h1", "1. Описание проекта"))
    story.append(p("h2", "1.1. Цель проекта"))
    story.append(
        p(
            "body",
            "Разработка Telegram-бота с RAG-системой для автоматизации консультаций "
            "клиентов по аренде загородных домов: ответы на вопросы об объектах, "
            "подбор по критериям, приём заявок и заказ обратного звонка с уведомлением менеджеров.",
        )
    )
    story.append(p("h2", "1.2. Используемые технологии"))
    story.append(
        table(
            [
                ["Компонент", "Технология"],
                ["Интерфейс", "Telegram Bot API, python-telegram-bot"],
                ["Логика", "Python 3.12"],
                ["RAG", "LangChain + FAISS"],
                ["LLM", "OpenAI API (gpt-4o-mini) / ProxyAPI"],
                ["Данные", "JSON (50 объектов), фото объектов"],
                ["Деплой", "Beget VPS, systemd"],
            ],
            [5 * cm, w - 5 * cm],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(p("h2", "1.3. Среда развёртывания"))
    story.extend(
        bullets(
            [
                "Сервер Linux (VPS Beget), сервис rental-bot 24/7",
                "Векторный индекс FAISS на сервере",
                "Секреты в .env (BOT_TOKEN, API_KEY)",
            ]
        )
    )

    # 2
    story.append(p("h1", "2. Основные функции бота"))
    story.append(p("h2", "2.1. Функциональные требования"))
    story.append(p("body", "<b>Консультации (RAG):</b>"))
    story.extend(
        bullets(
            [
                "Ответы на вопросы о домах, ценах, условиях аренды",
                "Только факты из базы знаний, без выдуманных данных",
                "Персонализация: сеньор / сеньорита, обращение по имени",
            ]
        )
    )
    story.append(p("body", "<b>Подбор домов:</b>"))
    story.extend(
        bullets(
            [
                "Фильтры: регион, число гостей, бюджет",
                "Карточка объекта с фото и inline-кнопками",
            ]
        )
    )
    story.append(p("body", "<b>Заявки:</b>"))
    story.extend(
        bullets(
            [
                "С карточки дома: телефон → время звонка → сообщение",
                "Валидация номера (+7 / 7 / 8)",
                "Уведомление менеджерам в Telegram-группу",
            ]
        )
    )
    story.append(p("body", "<b>Обратный звонок:</b>"))
    story.extend(bullets(["Телефон → удобное время → описание ситуации"]))
    story.append(p("body", "<b>Дополнительно:</b>"))
    story.extend(
        bullets(
            [
                f"Персона «{BOT_NAME}» — итальянский стиль общения",
                "Подарок клиенту — ссылка на альбом Suno после заявки",
            ]
        )
    )
    story.append(p("h2", "2.2. Архитектура"))
    story.append(
        p(
            "mono",
            "Telegram → bot.py → rag.py (FAISS + LangChain + LLM)<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↑<br/>"
            "data/properties.json + photos",
        )
    )

    # 3
    story.append(p("h1", "3. Реализация проекта"))
    story.append(p("h2", "3.1. База знаний"))
    story.extend(
        bullets(
            [
                "50 объектов недвижимости в properties.json",
                "Фото для карточек домов",
                "Системный промпт в prompts/system.txt",
            ]
        )
    )
    story.append(p("h2", "3.2. RAG-ассистент"))
    story.extend(
        bullets(
            [
                "Построение FAISS-индекса (build_index.py)",
                "Retrieval + генерация ответа LLM",
            ]
        )
    )
    story.append(p("h2", "3.3. Telegram-бот"))
    story.extend(
        bullets(
            [
                "Онбординг, inline-меню, диалоги заявок",
                "Деплой: python deploy_bot.py",
            ]
        )
    )

    # 4
    story.append(p("h1", "4. Внедрение и передача"))
    story.extend(
        bullets(
            [
                "Бот развёрнут на VPS и работает в режиме polling",
                "Заявки сохраняются в applications.json",
                "Менеджеры получают уведомления в группу",
                f"Исходный код: {GITHUB_URL}",
            ]
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(p("h2", "Демо"))
    story.extend(
        bullets(
            [
                f"Telegram-бот: {BOT_URL} ({BOT_USERNAME})",
                f"Группа заявок: {MANAGER_GROUP_URL}",
            ]
        )
    )

    # 5
    story.append(p("h1", "5. Сроки, стоимость и условия"))
    story.append(
        table(
            [
                ["Параметр", "Значение"],
                ["Срок разработки MVP", "2 недели (по ТЗ курса)"],
                ["Стоимость", "По договорённости с заказчиком"],
                ["Поддержка", "Доработки по отдельному соглашению"],
            ],
            [5.5 * cm, w - 5.5 * cm],
        )
    )

    # 6 — скриншоты
    story.append(PageBreak())
    story.append(p("h1", "6. Аналогичный кейс — скриншоты работы бота"))
    story.append(
        p(
            "body",
            "Ниже — основные экраны Telegram-бота. Полный комплект также в папке «скриншоты».",
        )
    )

    shot_labels = {
        "01-start-menu": "6.1. Приветствие и главное меню",
        "02-house-search": "6.2. Подбор дома — фильтры",
        "03-house-card": "6.3. Карточка дома с фото",
        "04-rag-consultation": "6.4. RAG-консультация",
        "05-application": "6.5. Оформление заявки",
        "06-success-gift": "6.6. Подтверждение и подарок",
    }

    if shots_dir.is_dir():
        for png in sorted(shots_dir.glob("*.png")):
            label = shot_labels.get(png.stem, png.stem.replace("-", " "))
            story.append(Spacer(1, 0.4 * cm))
            story.append(p("caption", label))
            img = RlImage(str(png))
            img_w, img_h = img.wrap(w, 20 * cm)
            scale = min(w / img_w, 14 * cm / img_h, 1.0)
            img.drawWidth = img_w * scale
            img.drawHeight = img_h * scale
            story.append(img)
            story.append(Spacer(1, 0.3 * cm))

    story.append(Spacer(1, 0.5 * cm))
    story.append(p("h2", "Ссылки"))
    story.extend(
        bullets(
            [
                f"GitHub: {GITHUB_URL}",
                f"Бот: {BOT_URL}",
                f"Группа заявок: {MANAGER_GROUP_URL}",
            ]
        )
    )

    doc.build(story)


def build_pdf(md_path: Path, pdf_path: Path) -> None:
    """Собрать КП-PDF через ReportLab (md_path сохранён для совместимости)."""
    shots_dir = md_path.parent / "скриншоты"
    if not shots_dir.is_dir():
        shots_dir = SCREENSHOTS
    build_kp_pdf(pdf_path, shots_dir)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "образец").mkdir()
    (OUT / "коммерческое-предложение").mkdir()
    (OUT / "отчёт").mkdir()
    (OUT / "github").mkdir()
    (OUT / "портфолио").mkdir()
    SCREENSHOTS.mkdir()

    # Образец Zerocoder
    sample_src = ROOT / "docs" / "submission" / "КП. Пример. ТГ-бот.pdf"
    if not sample_src.exists():
        sample_src = ROOT / "КП. Пример. ТГ-бот.pdf"
    if sample_src.exists():
        shutil.copy2(sample_src, OUT / "образец" / sample_src.name)

    assignment = ROOT / "docs" / "zerocoder-assignment.txt"
    if assignment.exists():
        shutil.copy2(assignment, OUT / "образец" / "задание-курса.txt")

    # Скриншоты
    make_chat_screenshot(
        SCREENSHOTS / "01-start-menu.png",
        title=BOT_NAME,
        messages=[
            (
                f"Ciao, сеньор! 🇮🇹 Я — {BOT_NAME}, ваш bellissimo консультант по аренде домов!\n\n"
                "Выберите действие кнопками или задайте вопрос про дома:",
                False,
            ),
        ],
        buttons=[
            "🏠 Подобрать casa    📞 Перезвоните мне",
            f"☎️ {COMPANY_PHONE} — скопировать",
        ],
    )

    make_chat_screenshot(
        SCREENSHOTS / "02-house-search.png",
        title=BOT_NAME,
        messages=[
            ("Perfetto, сеньор! Подберём идеальную casa 🏡🇮🇹\n\nШаг 1 из 3 — где хотите отдохнуть?", False),
        ],
        buttons=[
            "🌊 Mare — у моря",
            "🏡 Подмосковье    ☀️ Краснодар",
            "🏖 Крым    🌍 Ovunque — любой",
            "❌ Annulla",
        ],
        height=950,
    )

    make_house_card_screenshot(SCREENSHOTS / "03-house-card.png")

    make_chat_screenshot(
        SCREENSHOTS / "04-rag-consultation.png",
        title=BOT_NAME,
        messages=[
            ("Нужен дом у моря до 100000 рублей на 4 человека", True),
            (
                "Сеньор, ecco! 🌊 Нашёл bellissimo варианты у моря:\n\n"
                "• house-008 — Семейный дом у пляжа #8, Евпатория, 4–6 гостей, 95 000 ₽\n"
                "• house-029 — …\n\n"
                "Capisce? Могу показать карточку — жмите «Подобрать casa»!",
                False,
            ),
        ],
        height=850,
    )

    make_chat_screenshot(
        SCREENSHOTS / "05-application.png",
        title=BOT_NAME,
        messages=[
            (
                "Fantastico, сеньор! Заявка на 🏡 Семейный дом у пляжа #8 ✨\n\n"
                "Grazie! Теперь телефон для связи 📞\n"
                f"Формат: +7 9XX…\nНаш номер: {COMPANY_PHONE}",
                False,
            ),
            ("89564567898", True),
            ("Perfetto! Когда удобно связаться? 🕐\nНапример: завтра после 18:00", False),
        ],
        height=900,
    )

    make_chat_screenshot(
        SCREENSHOTS / "06-success-gift.png",
        title=BOT_NAME,
        messages=[
            (
                "🎉 Perfetto, сеньор! Заявка принята — che bella cosa! 🇮🇹✨\n\n"
                f"{BOT_NAME} уже передал её менеджеру — скоро перезвоним alla grande! 📞🏡",
                False,
            ),
            (
                f"Ciao, сеньор! Пока менеджер готовит casa — маленький regalo от {BOT_NAME} 🎁\n\n"
                "🎁 Подарок — альбом «Свинг Бантидос»\n"
                "https://suno.com/@lego_1",
                False,
            ),
        ],
        height=900,
    )

    kp_md = OUT / "коммерческое-предложение" / "КП-Джонни-Рентино.md"
    write_kp_markdown(kp_md)

    build_pdf(kp_md, OUT / "коммерческое-предложение" / "КП-Джонни-Рентино.pdf")

    write_report(OUT / "отчёт" / "отчёт-для-платформы.txt")
    write_portfolio(OUT / "портфолио" / "описание-проекта-для-резюме.md")
    (OUT / "github" / "ссылка.txt").write_text(
        f"{GITHUB_URL}\n{BOT_URL}\n{MANAGER_GROUP_URL}\n",
        encoding="utf-8",
    )
    write_readme(OUT / "README.md")
    (OUT / "КАК-СДАТЬ.txt").write_text(
        f"""КАК СДАТЬ ВЫПУСКНОЙ ПРОЕКТ НА ZEROCODER
======================================

1. Урок «Подведение итогов…» на university.zerocoder.ru

2. Прикрепите: коммерческое-предложение/КП-Джонни-Рентино.pdf

3. Текст в поле сдачи: отчёт/отчёт-для-платформы.txt

4. Ссылки:
   GitHub: {GITHUB_URL}
   Бот: {BOT_URL} ({BOT_USERNAME})
   Группа заявок: {MANAGER_GROUP_URL}

5. Резюме + портфолио (см. портфолио/описание-проекта-для-резюме.md)

6. Образец Zerocoder: образец/КП. Пример. ТГ-бот.pdf

Пересборка: python scripts/build_submission_pack.py
""",
        encoding="utf-8",
    )

    # Copy screenshots into KP folder for convenience
    kp_shots = OUT / "коммерческое-предложение" / "скриншоты"
    kp_shots.mkdir(exist_ok=True)
    for png in SCREENSHOTS.glob("*.png"):
        shutil.copy2(png, kp_shots / png.name)

    print(f"OK: {OUT}")


if __name__ == "__main__":
    main()
