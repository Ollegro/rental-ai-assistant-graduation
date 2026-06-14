from __future__ import annotations

import logging

from telegram import User
from telegram.ext import ContextTypes

from config import get_manager_chat_id

logger = logging.getLogger(__name__)


async def send_callback_request_to_manager(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    user: User,
    full_name: str,
    address: str,
    phone: str,
    preferred_time: str,
    situation: str,
) -> bool:
    chat_id = get_manager_chat_id()
    if chat_id is None:
        logger.warning("MANAGER_CHAT_ID не задан — уведомление в группу пропущено")
        return False

    username = f"@{user.username}" if user.username else "—"
    text = (
        "📞 Заказ обратного звонка\n\n"
        f"Клиент: {full_name} ({address})\n"
        f"Telegram: {username}\n"
        f"ID: {user.id}\n"
        f"Телефон: {phone}\n"
        f"Удобное время: {preferred_time}\n"
        f"Ситуация: {situation or '—'}"
    )

    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception:
        logger.exception("Не удалось отправить заявку на обратный звонок в группу %s", chat_id)
        return False


async def send_house_application_to_manager(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    user: User,
    full_name: str,
    address: str,
    phone: str,
    property_id: str,
    property_title: str,
    preferred_time: str,
    situation: str,
) -> bool:
    chat_id = get_manager_chat_id()
    if chat_id is None:
        logger.warning("MANAGER_CHAT_ID не задан — уведомление в группу пропущено")
        return False

    username = f"@{user.username}" if user.username else "—"
    text = (
        "✨ Заявка на дом\n\n"
        f"Объект: {property_title} ({property_id})\n"
        f"Клиент: {full_name} ({address})\n"
        f"Telegram: {username}\n"
        f"ID: {user.id}\n"
        f"Телефон: {phone}\n"
        f"Удобное время: {preferred_time}\n"
        f"Сообщение: {situation or '—'}"
    )

    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception:
        logger.exception("Не удалось отправить заявку на дом в группу %s", chat_id)
        return False
