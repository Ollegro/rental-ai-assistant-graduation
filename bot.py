"""Telegram-бот: консультации по аренде домов (RAG) и приём заявок."""
from __future__ import annotations

import logging
import re

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from applications import save_application
from config import get_bot_token
from knowledge_base import find_property_by_id, format_properties_summary, load_properties
from rag import RentalAssistant

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

(
    APPLY_PROPERTY,
    APPLY_NAME,
    APPLY_PHONE,
    APPLY_COMMENT,
) = range(4)

CANCEL_WORDS = {"отмена", "cancel", "/cancel"}


def get_assistant(context: ContextTypes.DEFAULT_TYPE) -> RentalAssistant:
    if "assistant" not in context.application.bot_data:
        context.application.bot_data["assistant"] = RentalAssistant()
    return context.application.bot_data["assistant"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Здравствуйте! Я ИИ-консультант компании по аренде домов.\n\n"
        "Могу рассказать об объектах, помочь подобрать дом и принять заявку на аренду.\n\n"
        "Команды:\n"
        "/houses — список доступных домов\n"
        "/apply — оформить заявку на аренду\n"
        "/help — подсказка\n\n"
        "Или просто напишите вопрос, например:\n"
        "«Нужен дом у моря до 130000 рублей на июль»"
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Задайте вопрос об аренде в свободной форме — я отвечу на основе базы объектов.\n"
        "Для заявки используйте /apply или напишите «хочу оформить заявку»."
    )


async def houses_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    properties = load_properties()
    await update.message.reply_text(format_properties_summary(properties))


async def consult(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = (update.message.text or "").strip()
    if not question:
        return

    await update.message.chat.send_action("typing")
    try:
        answer = get_assistant(context).answer(question)
    except Exception as exc:
        logger.exception("RAG error")
        await update.message.reply_text(
            f"Не удалось получить ответ от ассистента: {exc}\n"
            "Проверьте API-ключ в .env и перезапустите бота."
        )
        return

    await update.message.reply_text(answer)


async def apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    properties = load_properties()
    ids = ", ".join(item["id"] for item in properties)
    context.user_data["application"] = {}

    await update.message.reply_text(
        f"Оформление заявки на аренду.\n\n"
        f"Укажите ID интересующего дома ({ids})\n"
        f"или напишите «отмена».",
        reply_markup=ReplyKeyboardRemove(),
    )
    return APPLY_PROPERTY


async def apply_property(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text("Заявка отменена.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    properties = load_properties()
    item = find_property_by_id(properties, text)
    if not item:
        await update.message.reply_text(
            "Не нашёл такой ID. Проверьте список через /houses и введите ID снова."
        )
        return APPLY_PROPERTY

    context.user_data.setdefault("application", {})
    context.user_data["application"]["property_id"] = item["id"]
    context.user_data["application"]["property_title"] = item["title"]

    await update.message.reply_text(
        f"Выбран объект: {item['title']} ({item['id']})\n"
        "Как к вам обращаться? Укажите имя и фамилию."
    )
    return APPLY_NAME


async def apply_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text("Заявка отменена.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    if len(text) < 2:
        await update.message.reply_text("Имя слишком короткое. Введите имя ещё раз.")
        return APPLY_NAME

    context.user_data["application"]["full_name"] = text
    await update.message.reply_text("Укажите телефон для связи (например, +7 999 123-45-67).")
    return APPLY_PHONE


async def apply_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text("Заявка отменена.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    digits = re.sub(r"\D", "", text)
    if len(digits) < 10:
        await update.message.reply_text("Похоже, номер указан неверно. Введите телефон ещё раз.")
        return APPLY_PHONE

    context.user_data["application"]["phone"] = text
    await update.message.reply_text(
        "Добавьте комментарий к заявке (даты, количество гостей) "
        "или отправьте «-», если комментария нет."
    )
    return APPLY_COMMENT


async def apply_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text("Заявка отменена.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    app_data = context.user_data.get("application", {})
    comment = "" if text == "-" else text
    user = update.effective_user

    record = save_application(
        user_id=user.id,
        username=user.username,
        full_name=app_data.get("full_name", ""),
        phone=app_data.get("phone", ""),
        property_id=app_data.get("property_id", ""),
        property_title=app_data.get("property_title", ""),
        comment=comment,
    )

    context.user_data.pop("application", None)
    await update.message.reply_text(
        "Заявка принята!\n\n"
        f"Номер заявки: {record['id']}\n"
        f"Объект: {record['property_title']} ({record['property_id']})\n"
        f"Имя: {record['full_name']}\n"
        f"Телефон: {record['phone']}\n"
        f"Комментарий: {record['comment'] or '—'}\n\n"
        "Менеджер свяжется с вами в ближайшее время.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("application", None)
    await update.message.reply_text("Действие отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def build_application() -> Application:
    token = get_bot_token()
    if not token:
        raise ValueError("BOT_TOKEN не задан. Укажите токен Telegram-бота в .env")

    app = Application.builder().token(token).build()

    apply_handler = ConversationHandler(
        entry_points=[
            CommandHandler("apply", apply_start),
            MessageHandler(
                filters.Regex(re.compile(r"(оформить\s+заявку|оставить\s+заявку|хочу\s+аренд)", re.I)),
                apply_start,
            ),
        ],
        states={
            APPLY_PROPERTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_property)],
            APPLY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_name)],
            APPLY_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_phone)],
            APPLY_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("houses", houses_command))
    app.add_handler(apply_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, consult))

    return app


def main() -> None:
    application = build_application()
    logger.info("Бот запущен. Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
