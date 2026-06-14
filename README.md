# ИИ-ассистент для аренды домов

Telegram-бот с RAG-системой для консультаций клиентов по аренде загородной недвижимости.

## Возможности

- ответы на вопросы об объектах, ценах и условиях аренды;
- подбор домов по запросу (локация, бюджет, удобства);
- приём заявок на аренду с сохранением в JSON;
- поиск по базе знаний через **FAISS** + **LangChain**;
- генерация ответов через LLM API (OpenAI / ProxyAPI).

## Архитектура

```
Telegram Bot
     ↓
bot.py (диалог, заявки)
     ↓
rag.py (RAG: retrieval + LLM)
     ↓
FAISS ← embeddings ← data/properties.json
     ↓
LLM API (gpt-4o-mini)
```

## Быстрый старт

### 1. Зависимости

```powershell
cd "Подведение итогов и разработка выпускного проекта"
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
```

### 2. Настройка `.env`

```powershell
copy .env.example .env
```

Заполните:

- `API_KEY` или `PROXYAPI_KEY` — ключ LLM API;
- `BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather).

### 3. Сборка индекса FAISS

```powershell
python build_index.py
```

При изменении `data/properties.json`:

```powershell
python build_index.py --force
```

### 4. Тест RAG (без Telegram)

```powershell
python test_rag.py "Нужен дом с бассейном до 100000 рублей"
```

### 5. Запуск бота

```powershell
python bot.py
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкция |
| `/houses` | Список всех объектов |
| `/apply` | Оформить заявку на аренду |
| `/help` | Подсказка |
| `/cancel` | Отмена заявки |

Свободный текст — консультация через RAG.

## Структура проекта

| Файл / папка | Назначение |
|--------------|------------|
| `bot.py` | Telegram-бот |
| `rag.py` | RAG: FAISS + LangChain + LLM |
| `knowledge_base.py` | Загрузка и форматирование объектов |
| `applications.py` | Сохранение заявок |
| `config.py` | Настройки из `.env` |
| `build_index.py` | Построение FAISS-индекса |
| `test_rag.py` | Локальный тест ассистента |
| `data/properties.json` | База знаний объектов |
| `data/applications.json` | Заявки (создаётся автоматически) |
| `data/faiss_index/` | Векторная база |
| `prompts/system.txt` | Системный промпт ассистента |

## Промпты

Системный промпт в `prompts/system.txt` задаёт роль консультанта, правила работы с контекстом и формат ответа.

RAG передаёт в модель релевантные фрагменты из FAISS перед каждым ответом.

## Тестирование (по ТЗ)

1. **Ассистент** — `python test_rag.py` или диалог в Telegram;
2. **Поиск по базе** — вопросы про локацию, цену, удобства;
3. **Telegram-бот** — `/houses`, свободный текст, `/apply`;
4. **Заявки** — проверка `data/applications.json` после `/apply`.

## Выпускной проект Zerocoder

Тема: **ИИ-система для компании, предоставляющей дома в аренду**.

Стек: Python, LangChain, FAISS, Telegram Bot API, LLM API.

Срок сдачи материалов: см. задание на платформе (КП, отчёт, GitHub, резюме).
