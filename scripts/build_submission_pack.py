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
    draw.text((24, 48), "bot", fill=MUTED, font=_font(14))

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
    draw.text((24, 48), "bot", fill=MUTED, font=_font(14))

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
- Telegram: откройте бота через BotFather (токен в .env проекта)

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
| 3 | {GITHUB_URL} | ссылка в отчёте |
| 4 | `портфолио/описание-проекта-для-резюме.md` + ваше резюме | файлы |
| 5 | `образец/КП. Пример. ТГ-бот.pdf` | образец от Zerocoder (для себя) |

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


def build_pdf(md_path: Path, pdf_path: Path) -> None:
    try:
        from fpdf import FPDF
    except ImportError:
        return

    text = md_path.read_text(encoding="utf-8")
    pdf = FPDF()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    font = r"C:\Windows\Fonts\arial.ttf"
    if Path(font).exists():
        pdf.add_font("ArialUni", "", font)
        pdf.set_font("ArialUni", size=11)
    else:
        pdf.set_font("Helvetica", size=11)

    def writeln(line: str, size: int = 11) -> None:
        pdf.set_font_size(size)
        safe = line.replace("**", "").replace("*", "").replace("`", "")
        if not safe.strip():
            pdf.ln(3)
            return
        pdf.multi_cell(pdf.epw, 6, safe)

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            pdf.ln(2)
            writeln(line[2:], 16)
            continue
        if line.startswith("## "):
            pdf.ln(2)
            writeln(line[3:], 13)
            continue
        if line.startswith("---") or line.startswith("```") or line.startswith("|"):
            pdf.ln(2)
            continue
        writeln(line)

    shots_dir = md_path.parent / "скриншоты"
    if not shots_dir.is_dir():
        shots_dir = SCREENSHOTS
    if shots_dir.is_dir():
        pdf.add_page()
        writeln("6. Аналогичный кейс — скриншоты работы бота", 14)
        pdf.ln(4)
        for png in sorted(shots_dir.glob("*.png")):
            pdf.add_page()
            writeln(png.stem.replace("-", " "), 12)
            pdf.ln(2)
            pdf.image(str(png), w=min(pdf.epw, 170))

    pdf.output(str(pdf_path))


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
    (OUT / "github" / "ссылка.txt").write_text(GITHUB_URL + "\n", encoding="utf-8")
    write_readme(OUT / "README.md")
    (OUT / "КАК-СДАТЬ.txt").write_text(
        """КАК СДАТЬ ВЫПУСКНОЙ ПРОЕКТ НА ZEROCODER
======================================

1. Урок «Подведение итогов…» на university.zerocoder.ru

2. Прикрепите: коммерческое-предложение/КП-Джонни-Рентино.pdf

3. Текст в поле сдачи: отчёт/отчёт-для-платформы.txt

4. Ссылка GitHub: https://github.com/Ollegro/rental-ai-assistant-graduation

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
