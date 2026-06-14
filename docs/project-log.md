# Журнал проекта (память для Agent)

Краткая хронология решений. Новые записи — **сверху**.  
Секреты и токены сюда не писать.

---

## 2026-06-14 — Автоопределение обращения по имени

- После ввода имени бот сам выбирает «сеньор» / «сеньорита» (`name_gender.py`).
- Вопрос с кнопками только для унисекс и неоднозначных имён (Саша, Женя и т.п.).
- Убрана кнопка «Просто по имени» из онбординга.

**Проверка:** `/start` → «Мария» (без вопроса); «Саша» → выбор сеньор/сеньорита.

---

## 2026-06-14 — Inline-кнопки вместо reply-клавиатуры

- Главное меню переведено на `InlineKeyboardMarkup` (`keyboards.py`): дома, заявка, помощь, профиль.
- Обработчик `menu_callback` по `menu:*`; заявка — entry point `menu:apply` в `ConversationHandler` (`per_message=True`).
- Reply-клавиатура убрана (`ReplyKeyboardRemove`); команды `/help`, `/houses`, `/profile` работают и из callback.
- Деплой: `bot.py` + `keyboards.py` → VPS, сервис `rental-bot`.

**Проверка:** `/start` → «👇 Меню» с inline-кнопками; нажатие 🏠 / ✨ / ❓ / 👤.

---

## 2026-06-14 — Память Cursor, подарок Suno, без звуков

- Убраны аудио-сообщения (`sounds.py`) — перегружали диалог.
- Подарок после прощания или успешной `/apply`: ссылка на профиль Suno + текст «выберите песню» (`gifts.py`, `SUNO_PROFILE_URL` в `config.py`).
- Исправлен `/start`: падал из‑за MarkdownV2 (`!` не экранирован); онбординг вынесен из сломанного `ConversationHandler`.
- Добавлены `AGENTS.md`, `.cursor/rules/project-memory.mdc`, этот журнал.

**Проверка:** `/start` → имя → пол → меню; «спасибо, пока» → подарок со ссылкой.

---

## 2026-06-14 — Джонни Рентино, кнопки, профиль пользователя

- Персона **Джонни Рентино** в `prompts/system.txt` и текстах бота.
- Онбординг: имя + пол (сеньор / сеньорита / по имени) → `data/users.json`.
- Reply-клавиатура: дома, заявка, помощь, профиль.
- `/houses` — несколько сообщений (50 домов > лимит Telegram).
- Деплой: `python deploy_bot.py` → VPS `/opt/rental-bot`, сервис `rental-bot`.

**Ограничение деплоя:** не трогать `/opt/n8n`, `/var/www`, Docker volumes.

---

## 2026-06-14 — Базовый бот + RAG + VPS

- Telegram-бот + RAG (LangChain, FAISS, ProxyAPI).
- 50 объектов в `data/properties.json`.
- FAISS на Windows: `%LOCALAPPDATA%/rental-ai-assistant/faiss_index`.
- GitHub: `Ollegro/rental-ai-assistant-graduation`.

**Запуск локально:** `python build_index.py` → `python bot.py` (не параллельно с VPS).
