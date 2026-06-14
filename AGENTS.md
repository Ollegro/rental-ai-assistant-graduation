# AGENTS.md — контекст для Cursor Agent

Выпускной проект Zerocoder: **Telegram-бот + RAG** для консультаций по аренде домов.

## С чего начать

1. Прочитай **`docs/project-log.md`** — хронология решений и деплоя.
2. Секреты только в **`.env`** и **`beget-vps/ssh.local.env`** (в Git не коммитить).
3. Не запускай локально `bot.py`, если бот уже работает на VPS (один `BOT_TOKEN` = один polling).

## Стек и архитектура

```
Telegram → bot.py → rag.py (FAISS + LangChain + LLM API)
                      ↑
              data/properties.json (50 домов)
              data/photos/ (фото объектов)
```

| Модуль | Назначение |
|--------|------------|
| `bot.py` | Диалог, онбординг, inline-меню, заявки, обратный звонок |
| `rag.py` | Retrieval + ответ LLM |
| `house_search.py` | Подбор домов по региону / гостям / бюджету |
| `property_photos.py` | Фото объектов в карточках |
| `validators.py` | Валидация телефона и времени звонка |
| `notifications.py` | Уведомления менеджерам в Telegram-группу |
| `personality.py` | **Джонни Рентино**, сеньор/сеньорита |
| `users.py` | Профили пользователей → `data/users.json` |
| `gifts.py` | Подарок-ссылка на Suno после прощания/заявки |
| `keyboards.py` | Inline-кнопки меню и подбора |
| `deploy_bot.py` | Деплой на Beget VPS → `/opt/rental-bot`, systemd `rental-bot` |

## Персона бота

- Имя: **Джонни Рентино**, итальянский акцент, шутки, эмодзи.
- При `/start`: имя → кнопки пола (сеньор / сеньорита) → inline-меню.
- RAG получает пол и имя из профиля (`get_rag_client_context`).
- Промпт: `prompts/system.txt`.

## Команды и UX

- Inline-меню: **🏠 Подобрать casa**, **📞 Перезвоните мне**, **☎️ скопировать номер**.
- Подбор домов: регион → гости → бюджет → карточка с фото.
- **✨ Оформить заявку** на карточке: телефон → время → сообщение → подтверждение + подарок Suno.
- Обратный звонок: телефон → время → ситуация → группа менеджеров (`MANAGER_CHAT_ID`).
- `/apply` — заявка по ID дома.
- Прощание или успешная заявка → подарок: https://suno.com/@lego_1

## FAISS и пути

- **Windows:** `%LOCALAPPDATA%/rental-ai-assistant/faiss_index` (кириллица в пути проекта ломает FAISS).
- **VPS/Linux:** `data/faiss_index` или `FAISS_DIR` в `.env`.
- Пересборка: `python build_index.py --force`.

## Деплой VPS (Beget)

```powershell
python deploy_bot.py
```

- Путь на сервере: `/opt/rental-bot`
- **Не трогать:** `/opt/n8n`, `/var/www`, Docker volumes.
- Скрипт удаляет только `venv` и `faiss_index` внутри `/opt/rental-bot`.
- Логи: `journalctl -u rental-bot -f`

## GitHub

https://github.com/Ollegro/rental-ai-assistant-graduation

## Память между сессиями

Полная история чата Cursor **не** хранится в репозитории. Актуальный контекст — **`docs/project-log.md`**. После значимых изменений агент должен дописывать туда запись (см. правило `.cursor/rules/project-memory.mdc`).
