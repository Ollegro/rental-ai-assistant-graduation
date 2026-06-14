"""Telegram-бот: консультации по аренде домов (RAG) и приём заявок."""
from __future__ import annotations

import logging
import re

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from applications import save_application
from config import get_bot_token
from keyboards import (
    BTN_APPLY,
    BTN_HELP,
    BTN_HOUSES,
    BTN_PROFILE,
    GENDER_FEMALE,
    GENDER_MALE,
    GENDER_NEUTRAL,
    gender_keyboard,
    main_menu_keyboard,
)
from knowledge_base import (
    find_property_by_id,
    format_properties_summary_messages,
    load_properties,
    split_text_for_telegram,
)
from personality import BOT_NAME, get_address, get_rag_client_context
from gifts import format_gift_message, is_farewell
from rag import RentalAssistant
from users import get_user_profile, save_user_profile

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

ONBOARDING_NAME = "name"
ONBOARDING_GENDER = "gender"

CANCEL_WORDS = {"отмена", "cancel", "/cancel"}

GENDER_FROM_CALLBACK = {
    GENDER_MALE: "male",
    GENDER_FEMALE: "female",
    GENDER_NEUTRAL: "neutral",
}


def get_assistant(context: ContextTypes.DEFAULT_TYPE) -> RentalAssistant:
    if "assistant" not in context.application.bot_data:
        context.application.bot_data["assistant"] = RentalAssistant()
    return context.application.bot_data["assistant"]


def load_profile(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> dict | None:
    cached = context.user_data.get("profile")
    if cached:
        return cached
    profile = get_user_profile(user_id)
    if profile:
        context.user_data["profile"] = profile
    return profile


def clear_onboarding(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("onboarding_step", None)
    context.user_data.pop("pending_name", None)


async def send_welcome_back(update: Update, profile: dict) -> None:
    address = get_address(profile)
    text = (
        f"Ciao, {address}! 🇮🇹 Я — {BOT_NAME}, ваш bellissimo консультант по аренде домов!\n\n"
        "Mamma mia, у нас столько прекрасных вилл — alla grande для отдыха! ☀️🏡\n\n"
        "Выберите действие кнопками ниже или просто напишите вопрос, capisce? 😄"
    )
    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(),
    )


async def send_conversation_gift(update: Update, profile: dict) -> None:
    address = get_address(profile)
    await update.message.reply_text(
        f"Ciao, {address}! Разговор окончен — было bellissimo пообщаться ☀️\n\n"
        f"{format_gift_message()}",
        reply_markup=main_menu_keyboard(),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_onboarding(context)
    context.user_data.pop("application", None)

    user = update.effective_user
    profile = load_profile(context, user.id)
    if profile:
        await send_welcome_back(update, profile)
        return

    context.user_data["onboarding_step"] = ONBOARDING_NAME
    await update.message.reply_text(
        f"Ciao! 🇮🇹 Я — {BOT_NAME}, ваш консультант по аренде домов!\n\n"
        "Прежде чем подбирать bellissimo виллы, познакомимся 😄\n"
        "Как вас зовут? Напишите имя:",
        reply_markup=ReplyKeyboardRemove(),
    )


async def start_and_end_apply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await start(update, context)
    return ConversationHandler.END


async def handle_onboarding_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    step = context.user_data.get("onboarding_step")
    if step == ONBOARDING_GENDER:
        await update.message.reply_text(
            "Почти готово! Выберите кнопку: 👨 Сеньор, 👩 Сеньорита или 🤝 Просто по имени 👇"
        )
        return

    if step != ONBOARDING_NAME:
        return

    text = (update.message.text or "").strip()
    if text.lower() in CANCEL_WORDS:
        clear_onboarding(context)
        await update.message.reply_text("Va bene! Когда будете готовы — /start 🇮🇹")
        return

    if len(text) < 2:
        await update.message.reply_text("Ehm… имя слишком короткое! ☕ Напишите ещё раз:")
        return

    context.user_data["pending_name"] = text
    context.user_data["onboarding_step"] = ONBOARDING_GENDER
    await update.message.reply_text(
        f"Perfetto, {text}! ✨\n\n"
        "А как мне к вам обращаться? Выберите кнопкой 👇",
        reply_markup=gender_keyboard(),
    )


async def onboard_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if context.user_data.get("onboarding_step") != ONBOARDING_GENDER:
        return

    gender = GENDER_FROM_CALLBACK.get(query.data or "")
    if not gender:
        return

    name = context.user_data.pop("pending_name", "").strip()
    if not name:
        clear_onboarding(context)
        await query.edit_message_text("Mamma mia, имя потерялось! Нажмите /start ещё раз 🙏")
        return

    user = update.effective_user
    profile = save_user_profile(
        user.id,
        name=name,
        gender=gender,
        username=user.username,
    )
    context.user_data["profile"] = profile
    clear_onboarding(context)
    address = get_address(profile)

    await query.edit_message_text(f"Grazie mille, {address}! 🇮🇹 Perfetto!")
    await query.message.reply_text(
        f"Теперь я буду обращаться правильно — {address} 😄\n\n"
        "Выберите действие кнопками или задайте вопрос про дома:",
        reply_markup=main_menu_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)
    await update.message.reply_text(
        f"Ecco, {address}! 😄 Я — {BOT_NAME}, всегда на связи.\n\n"
        "Задайте вопрос об аренде — отвечу с душой и по фактам, grazie! 🏡\n"
        "Кнопка «✨ Оформить заявку» или /apply — alla grande! ✨",
        reply_markup=main_menu_keyboard(),
    )


async def houses_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)
    properties = load_properties()
    parts = format_properties_summary_messages(properties)
    for index, part in enumerate(parts):
        if index == 0:
            await update.message.reply_text(
                f"Perfetto, {address}! Сейчас покажу все наши case 🏡🇮🇹\n\n{part}",
                reply_markup=main_menu_keyboard() if len(parts) == 1 else None,
            )
        else:
            is_last = index == len(parts) - 1
            await update.message.reply_text(
                part,
                reply_markup=main_menu_keyboard() if is_last else None,
            )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    profile = load_profile(context, update.effective_user.id)
    if not profile:
        await update.message.reply_text("Сначала познакомимся — нажмите /start 🇮🇹")
        return

    labels = {
        "male": "сеньор 👨",
        "female": "сеньорита 👩",
        "neutral": "просто по имени 🤝",
    }
    address = get_address(profile)
    await update.message.reply_text(
        f"👤 *Ваш профиль*\n\n"
        f"Имя: {profile['name']}\n"
        f"Обращение: {address}\n"
        f"Стиль: {labels.get(profile.get('gender', 'neutral'), '—')}",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def consult(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    profile = load_profile(context, update.effective_user.id)
    if not profile:
        await update.message.reply_text(
            f"Ciao! Я — {BOT_NAME} 🇮🇹\n"
            "Сначала познакомимся — нажмите /start, и я узнаю, как к вам обращаться 😊"
        )
        return

    question = (update.message.text or "").strip()
    if not question:
        return

    address = get_address(profile)
    if is_farewell(question):
        await update.message.reply_text(
            f"Arrivederci, {address}! Grazie mille за беседу — {BOT_NAME} всегда рядом 🇮🇹😄"
        )
        await send_conversation_gift(update, profile)
        return

    await update.message.chat.send_action("typing")
    try:
        answer = get_assistant(context).answer(
            question,
            client_context=get_rag_client_context(profile),
        )
    except Exception as exc:
        logger.exception("RAG error")
        address = get_address(profile)
        await update.message.reply_text(
            f"Mamma mia, {address}, {BOT_NAME} сейчас прихворел! 😅\n"
            f"Техническая деталь: {exc}\n"
            "Попробуйте чуть позже, capisce? 🙏",
            reply_markup=main_menu_keyboard(),
        )
        return

    parts = split_text_for_telegram(answer)
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        await update.message.reply_text(
            part,
            reply_markup=main_menu_keyboard() if is_last else None,
        )


async def route_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("onboarding_step"):
        await handle_onboarding_text(update, context)
        return
    await consult(update, context)


async def apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    profile = load_profile(context, update.effective_user.id)
    if not profile:
        await update.message.reply_text("Сначала /start — познакомимся, capisce? 🇮🇹")
        return ConversationHandler.END

    context.user_data["application"] = {}
    address = get_address(profile)

    await update.message.reply_text(
        f"Fantastico, {address}! Оформляем заявку с {BOT_NAME} ✨🇮🇹\n\n"
        "Сначала ID дома — кнопка «🏠 Список домов» или /houses.\n"
        "Напишите ID (например, house-001) или «отмена».",
        reply_markup=ReplyKeyboardRemove(),
    )
    return APPLY_PROPERTY


async def apply_property(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text(
            f"Arrivederci, {address}! Заявка отменена 🇮🇹 alla grande в другой раз! 😊",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    properties = load_properties()
    item = find_property_by_id(properties, text)
    if not item:
        await update.message.reply_text(
            f"Mamma mia, {address}, такого ID нет! 😅\n"
            "Загляните в «🏠 Список домов» и попробуйте снова, capisce?"
        )
        return APPLY_PROPERTY

    context.user_data.setdefault("application", {})
    context.user_data["application"]["property_id"] = item["id"]
    context.user_data["application"]["property_title"] = item["title"]

    if profile and profile.get("name"):
        context.user_data["application"]["full_name"] = profile["name"]
        await update.message.reply_text(
            f"Bellissimo, {address}! 🏡 {item['title']} ({item['id']}) — che bella cosa!\n\n"
            "Grazie! Теперь телефон для связи 📞\n"
            "Например: +7 999 123-45-67"
        )
        return APPLY_PHONE

    await update.message.reply_text(
        f"Bellissimo выбор! 🏡 {item['title']} ({item['id']})\n\n"
        "Как к вам обращаться? Имя и фамилия, perfetto!"
    )
    return APPLY_NAME


async def apply_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text(
            "Arrivederci, заявка отменена! 🇮🇹",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    if len(text) < 2:
        await update.message.reply_text("Ehm… имя слишком короткое! ☕ Введите ещё раз 😄")
        return APPLY_NAME

    context.user_data["application"]["full_name"] = text
    await update.message.reply_text(
        "Grazie! Теперь телефон для связи 📞\n"
        "Например: +7 999 123-45-67 — alla grande!"
    )
    return APPLY_PHONE


async def apply_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text(
            f"Arrivederci, {address}! Заявка отменена 🇮🇹",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    digits = re.sub(r"\D", "", text)
    if len(digits) < 10:
        await update.message.reply_text(
            f"Mamma mia, {address}, номер странный! 📱 Введите ещё раз, capisce?"
        )
        return APPLY_PHONE

    context.user_data["application"]["phone"] = text
    await update.message.reply_text(
        "Perfetto! 🌟 Добавьте комментарий — даты, гостей, пожелания…\n"
        "Или «-», если комментария нет, ecco!"
    )
    return APPLY_COMMENT


async def apply_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text(
            f"Arrivederci, {address}! Заявка отменена 🇮🇹",
            reply_markup=main_menu_keyboard(),
        )
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
        f"🎉 *Grazie mille, {address}!* Заявка принята — {BOT_NAME} радуется! 🇮🇹✨\n\n"
        f"Номер заявки: `{record['id']}`\n"
        f"Объект: {record['property_title']} ({record['property_id']}) 🏡\n"
        f"Имя: {record['full_name']}\n"
        f"Телефон: {record['phone']}\n"
        f"Комментарий: {record['comment'] or '—'}\n\n"
        "Менеджер свяжется с вами alla grande — скоро! ☀️ Ciao!",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    await send_conversation_gift(update, profile)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("application", None)
    clear_onboarding(context)
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)
    await update.message.reply_text(
        f"Va bene, {address}, отменено! 🇮🇹 {BOT_NAME} всегда здесь! 😊",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Ошибка при обработке update: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            f"Mamma mia! {BOT_NAME} споткнулся 😅 Попробуйте ещё раз или /start"
        )


def build_application() -> Application:
    token = get_bot_token()
    if not token:
        raise ValueError("BOT_TOKEN не задан. Укажите токен Telegram-бота в .env")

    app = Application.builder().token(token).build()

    apply_handler = ConversationHandler(
        entry_points=[
            CommandHandler("apply", apply_start),
            MessageHandler(filters.Regex(re.escape(BTN_APPLY)), apply_start),
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
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start_and_end_apply),
        ],
    )

    menu_filter = filters.Regex(
        re.compile(
            rf"^({re.escape(BTN_HOUSES)}|{re.escape(BTN_HELP)}|{re.escape(BTN_PROFILE)})$"
        )
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(onboard_gender, pattern=r"^gender:"))
    app.add_handler(apply_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("houses", houses_command))
    app.add_handler(MessageHandler(menu_filter, _menu_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text))
    app.add_error_handler(on_error)

    return app


async def _menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if text == BTN_HOUSES:
        await houses_command(update, context)
    elif text == BTN_HELP:
        await help_command(update, context)
    elif text == BTN_PROFILE:
        await profile_command(update, context)


def main() -> None:
    application = build_application()
    logger.info("%s запущен. Нажмите Ctrl+C для остановки.", BOT_NAME)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
