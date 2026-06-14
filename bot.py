"""Telegram-бот: консультации по аренде домов (RAG) и приём заявок."""
from __future__ import annotations

import asyncio
import logging
import re

from telegram import InputMediaPhoto, Update
from telegram.error import NetworkError, TimedOut
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
from config import get_bot_token, get_company_phone
from keyboards import (
    GENDER_FEMALE,
    GENDER_MALE,
    MENU_APPLY,
    MENU_CALLBACK,
    MENU_HOUSES,
    SEARCH_BUDGET_PREFIX,
    SEARCH_CANCEL,
    SEARCH_GUESTS_PREFIX,
    SEARCH_REGION_PREFIX,
    house_search_budget_keyboard,
    house_search_guests_keyboard,
    house_search_region_keyboard,
    house_search_results_keyboard,
    house_detail_keyboard,
    HOUSE_APPLY_PREFIX,
    HOUSE_PICK_PREFIX,
    inline_main_menu_keyboard,
    remove_reply_keyboard,
    unisex_gender_keyboard,
)
from house_search import MAX_RESULTS, filter_properties, format_search_results
from name_gender import detect_name_gender
from knowledge_base import (
    find_property_by_id,
    load_properties,
    property_to_text,
    split_text_for_telegram,
)
from personality import BOT_NAME, get_address, get_rag_client_context, house_application_accepted_text
from property_photos import get_property_photo_paths, property_photo_caption
from gifts import format_gift_message, is_farewell
from notifications import send_callback_request_to_manager, send_house_application_to_manager
from validators import (
    PHONE_INVALID_MESSAGE,
    format_ru_mobile_phone,
    normalize_ru_mobile_phone,
    validate_callback_time,
)
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
    APPLY_TIME,
    APPLY_SITUATION,
) = range(6)

HOUSE_REGION, HOUSE_GUESTS, HOUSE_BUDGET = range(10, 13)
CALLBACK_PHONE, CALLBACK_TIME, CALLBACK_SITUATION = range(20, 23)

APPLY_CONV = "apply"
HOUSE_SEARCH_CONV = "house_search"
CALLBACK_CONV = "callback"

ONBOARDING_NAME = "name"
ONBOARDING_GENDER = "gender"

CANCEL_WORDS = {"отмена", "cancel", "/cancel"}

GENDER_FROM_CALLBACK = {
    GENDER_MALE: "male",
    GENDER_FEMALE: "female",
}

HOUSE_OVERVIEW_HINTS = (
    "какие",
    "сколько",
    "есть",
    "список",
    "покаж",
    "что",
    "все",
    "ассортимент",
)
HOUSE_OVERVIEW_TOPICS = (
    "дом",
    "объект",
    "жиль",
    "коттедж",
    "вилл",
    "аренд",
    "сним",
)


def apply_phone_prompt_text() -> str:
    return (
        "Grazie! Теперь телефон для связи 📞\n"
        "Формат: +7 9XX XXX-XX-XX (только цифры, начало +7 / 7 / 8).\n"
        f"Наш номер: {get_company_phone()}"
    )


CALLBACK_PHONE_PROMPT = (
    "Укажите номер телефона, на который вам перезвонить 📱\n"
    "Формат: +7 9XX XXX-XX-XX (начинается с +7, 7 или 8, затем 9 и ещё 9 цифр)"
)

CALLBACK_TIME_PROMPT = (
    "Perfetto! Когда удобно связаться? 🕐\n"
    "Например: сегодня после 18:00, завтра с 10 до 12"
)

CALLBACK_SITUATION_PROMPT = (
    "Расскажите коротко о ситуации — что ищете, даты, пожелания 📝\n"
    "Или «-», если без комментария."
)


def conversation_key(update: Update, name: str) -> tuple[int | str, int]:
    return (name, update.effective_user.id, update.effective_chat.id)


def end_conversation(context: ContextTypes.DEFAULT_TYPE, update: Update, name: str) -> None:
    context.user_data.pop(conversation_key(update, name), None)


def set_conversation(
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
    name: str,
    state: int,
) -> None:
    context.user_data[conversation_key(update, name)] = state


def get_assistant(context: ContextTypes.DEFAULT_TYPE) -> RentalAssistant:
    if "assistant" not in context.application.bot_data:
        context.application.bot_data["assistant"] = RentalAssistant()
    return context.application.bot_data["assistant"]


def clear_active_dialogs(context: ContextTypes.DEFAULT_TYPE, update: Update) -> None:
    for name in (APPLY_CONV, HOUSE_SEARCH_CONV, CALLBACK_CONV):
        end_conversation(context, update, name)
    context.user_data.pop("application", None)
    context.user_data.pop("house_search", None)
    context.user_data.pop("callback", None)


def is_house_overview_question(text: str) -> bool:
    normalized = text.lower()
    has_hint = any(hint in normalized for hint in HOUSE_OVERVIEW_HINTS)
    has_topic = any(topic in normalized for topic in HOUSE_OVERVIEW_TOPICS)
    return has_hint and has_topic


async def send_text_reply(message, text: str, **kwargs):
    for attempt in range(2):
        try:
            return await message.reply_text(text, **kwargs)
        except (TimedOut, NetworkError):
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            raise


async def answer_house_overview(update: Update, context: ContextTypes.DEFAULT_TYPE, profile: dict) -> None:
    address = get_address(profile)
    total = len(load_properties())
    await send_text_reply(
        update.message,
        f"Bellissimo, {address}! У нас *{total} домов* для аренды 🏡\n\n"
        "Чтобы не перечислять всё стеной текста — нажмите «🏠 Подобрать дом»: "
        "регион → гости → бюджет, и я покажу лучшие варианты alla grande!",
        parse_mode="Markdown",
        reply_markup=inline_main_menu_keyboard(),
    )


async def warmup_assistant(application: Application) -> None:
    try:
        application.bot_data["assistant"] = RentalAssistant()
        logger.info("RAG assistant готов")
    except Exception:
        logger.exception("Не удалось прогреть RAG при старте бота")


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
        "Выберите действие кнопками под сообщением или просто напишите вопрос, capisce? 😄"
    )
    await update.effective_message.reply_text(
        text,
        reply_markup=inline_main_menu_keyboard(),
    )


async def send_conversation_gift(
    update: Update,
    profile: dict,
    *,
    intro: str | None = None,
) -> None:
    address = get_address(profile)
    if intro is None:
        intro = f"Ciao, {address}! Разговор окончен — было bellissimo пообщаться ☀️"
    await update.effective_message.reply_text(
        f"{intro}\n\n{format_gift_message()}",
        reply_markup=inline_main_menu_keyboard(),
    )


async def send_application_gift(update: Update, profile: dict) -> None:
    address = get_address(profile)
    await send_conversation_gift(
        update,
        profile,
        intro=(
            f"Ciao, {address}! Пока менеджер готовит casa — "
            f"маленький regalo от {BOT_NAME} 🎁"
        ),
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
    await update.effective_message.reply_text(
        f"Ciao! 🇮🇹 Я — {BOT_NAME}, ваш консультант по аренде домов!\n\n"
        "Прежде чем подбирать bellissimo виллы, познакомимся 😄\n"
        "Как вас зовут? Напишите имя:",
        reply_markup=remove_reply_keyboard,
    )


async def start_and_end_apply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await start(update, context)
    return ConversationHandler.END


async def finish_onboarding(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    name: str,
    gender: str,
    intro_prefix: str | None = None,
) -> None:
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

    message = update.effective_message
    if intro_prefix:
        await message.reply_text(intro_prefix)

    await message.reply_text(
        f"Grazie mille, {address}! 🇮🇹 Perfetto!\n\n"
        "Выберите действие кнопками под сообщением или задайте вопрос про дома:",
        reply_markup=inline_main_menu_keyboard(),
    )


async def handle_onboarding_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    step = context.user_data.get("onboarding_step")
    if step == ONBOARDING_GENDER:
        await update.message.reply_text(
            "Подскажите, пожалуйста: 👨 Сеньор или 👩 Сеньорита? Выберите кнопкой 👇",
            reply_markup=unisex_gender_keyboard(),
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

    gender = detect_name_gender(text)
    if gender:
        await finish_onboarding(
            update,
            context,
            name=text,
            gender=gender,
            intro_prefix=f"Perfetto, {text}! ✨",
        )
        return

    context.user_data["pending_name"] = text
    context.user_data["onboarding_step"] = ONBOARDING_GENDER
    await update.message.reply_text(
        f"Perfetto, {text}! ✨\n\n"
        "У вас универсальное имя — подскажите, как обращаться: сеньор или сеньорита? 👇",
        reply_markup=unisex_gender_keyboard(),
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

    await query.edit_message_text(f"Perfetto, {name}! ✨")
    await finish_onboarding(update, context, name=name, gender=gender)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_active_dialogs(context, update)
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)
    await update.effective_message.reply_text(
        f"Ecco, {address}! 😄 Я — {BOT_NAME}, всегда на связи.\n\n"
        "Задайте вопрос об аренде — отвечу с душой и по фактам, grazie! 🏡\n"
        "Или нажмите «🏠 Подобрать дом» / «📞 Заказать обратный звонок» — alla grande! ✨",
        reply_markup=inline_main_menu_keyboard(),
    )


async def houses_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()

    profile = load_profile(context, update.effective_user.id)
    if not profile:
        await update.effective_message.reply_text(
            f"Ciao! Я — {BOT_NAME} 🇮🇹\n"
            "Сначала познакомимся — нажмите /start 😊"
        )
        return ConversationHandler.END

    address = get_address(profile)
    context.user_data["house_search"] = {}
    end_conversation(context, update, APPLY_CONV)
    end_conversation(context, update, CALLBACK_CONV)
    context.user_data.pop("application", None)

    await update.effective_message.reply_text(
        f"Perfetto, {address}! Подберём идеальную casa 🏡🇮🇹\n\n"
        "Шаг 1 из 3 — где хотите отдохнуть?",
        reply_markup=house_search_region_keyboard(),
    )
    return HOUSE_REGION


async def house_search_end_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("house_search", None)
    await start(update, context)
    return ConversationHandler.END


async def house_search_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("house_search", None)
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)
    await update.effective_message.reply_text(
        f"Va bene, {address}! Подбор отменён 🇮🇹",
        reply_markup=inline_main_menu_keyboard(),
    )
    return ConversationHandler.END


async def house_search_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop("house_search", None)
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)
    await query.edit_message_text(
        f"Va bene, {address}! Подбор отменён 🇮🇹",
        reply_markup=inline_main_menu_keyboard(),
    )
    return ConversationHandler.END


async def house_region_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    region = (query.data or "").removeprefix(SEARCH_REGION_PREFIX)
    context.user_data.setdefault("house_search", {})["region"] = region

    await query.edit_message_text(
        "Bene! Шаг 2 из 3 — сколько гостей? 👥",
        reply_markup=house_search_guests_keyboard(),
    )
    return HOUSE_GUESTS


async def house_guests_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    guests = (query.data or "").removeprefix(SEARCH_GUESTS_PREFIX)
    context.user_data.setdefault("house_search", {})["guests"] = guests

    await query.edit_message_text(
        "Perfetto! Шаг 3 из 3 — бюджет в месяц? 💰",
        reply_markup=house_search_budget_keyboard(),
    )
    return HOUSE_BUDGET


async def house_budget_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    budget = (query.data or "").removeprefix(SEARCH_BUDGET_PREFIX)
    criteria = context.user_data.setdefault("house_search", {})
    criteria["budget"] = budget

    properties = load_properties()
    matched = filter_properties(
        properties,
        region=criteria.get("region", "any"),
        guests=criteria.get("guests", "any"),
        budget=budget,
    )
    text = format_search_results(
        matched,
        region=criteria.get("region", "any"),
        guests=criteria.get("guests", "any"),
        budget=budget,
        total_count=len(properties),
    )
    context.user_data.pop("house_search", None)

    shown = matched[:MAX_RESULTS]
    keyboard = house_search_results_keyboard(shown) if shown else inline_main_menu_keyboard()

    await query.edit_message_text("Grazie! Смотрю, что подходит alla grande… ✨")
    await query.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    return ConversationHandler.END


async def house_show_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    property_id = (query.data or "").removeprefix(HOUSE_PICK_PREFIX)
    item = find_property_by_id(load_properties(), property_id)
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if not item:
        await query.message.reply_text(
            f"Mamma mia, {address}, дом {property_id} не найден 😅",
            reply_markup=inline_main_menu_keyboard(),
        )
        return

    photos = get_property_photo_paths(item)
    if photos:
        await query.message.chat.send_action("upload_photo")
        media: list[InputMediaPhoto] = []
        for index, path in enumerate(photos):
            kwargs: dict = {"media": path.read_bytes()}
            if index == 0:
                kwargs["caption"] = property_photo_caption(item)
            media.append(InputMediaPhoto(**kwargs))
        await query.message.reply_media_group(media)

    parts = split_text_for_telegram(property_to_text(item))
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        await query.message.reply_text(
            part,
            reply_markup=house_detail_keyboard(property_id) if is_last else None,
        )


async def apply_from_house(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    end_conversation(context, update, HOUSE_SEARCH_CONV)
    end_conversation(context, update, CALLBACK_CONV)
    context.user_data.pop("house_search", None)

    profile = load_profile(context, update.effective_user.id)
    if not profile:
        await query.message.reply_text("Сначала /start — познакомимся, capisce? 🇮🇹")
        end_conversation(context, update, APPLY_CONV)
        return ConversationHandler.END

    property_id = (query.data or "").removeprefix(HOUSE_APPLY_PREFIX)
    item = find_property_by_id(load_properties(), property_id)
    address = get_address(profile)

    if not item:
        await query.message.reply_text(
            f"Mamma mia, {address}, дом не найден 😅",
            reply_markup=inline_main_menu_keyboard(),
        )
        end_conversation(context, update, APPLY_CONV)
        return ConversationHandler.END

    context.user_data["application"] = {
        "property_id": item["id"],
        "property_title": item["title"],
        "from_house": True,
    }
    if profile.get("name"):
        context.user_data["application"]["full_name"] = profile["name"]
        await query.message.reply_text(
            f"Fantastico, {address}! Заявка на 🏡 {item['title']} ({item['id']}) ✨\n\n"
            f"{apply_phone_prompt_text()}",
        )
        return APPLY_PHONE

    await query.message.reply_text(
        f"Bellissimo! 🏡 {item['title']} ({item['id']})\n\n"
        "Как к вам обращаться? Имя и фамилия, perfetto!",
        reply_markup=remove_reply_keyboard,
    )
    return APPLY_NAME


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    profile = load_profile(context, update.effective_user.id)
    if not profile:
        await update.effective_message.reply_text("Сначала познакомимся — нажмите /start 🇮🇹")
        return

    labels = {
        "male": "сеньор 👨",
        "female": "сеньорита 👩",
        "neutral": "просто по имени 🤝",
    }
    address = get_address(profile)
    await update.effective_message.reply_text(
        f"👤 *Ваш профиль*\n\n"
        f"Имя: {profile['name']}\n"
        f"Обращение: {address}\n"
        f"Стиль: {labels.get(profile.get('gender', 'neutral'), '—')}",
        parse_mode="Markdown",
        reply_markup=inline_main_menu_keyboard(),
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

    if is_house_overview_question(question):
        await answer_house_overview(update, context, profile)
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
        parts = split_text_for_telegram(answer)
        for index, part in enumerate(parts):
            is_last = index == len(parts) - 1
            await send_text_reply(
                update.message,
                part,
                reply_markup=inline_main_menu_keyboard() if is_last else None,
            )
    except (TimedOut, NetworkError):
        logger.exception("Telegram/network error while answering")
        await send_text_reply(
            update.message,
            f"Mamma mia, {address}, связь подвисла! 😅 Попробуйте ещё раз или "
            "нажмите «🏠 Подобрать дом», capisce?",
            reply_markup=inline_main_menu_keyboard(),
        )
    except Exception as exc:
        logger.exception("RAG error")
        await send_text_reply(
            update.message,
            f"Mamma mia, {address}, {BOT_NAME} сейчас прихворел! 😅\n"
            f"Техническая деталь: {exc}\n"
            "Попробуйте чуть позже, capisce? 🙏",
            reply_markup=inline_main_menu_keyboard(),
        )


async def route_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("onboarding_step"):
        await handle_onboarding_text(update, context)
        return
    await consult(update, context)


async def apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()

    profile = load_profile(context, update.effective_user.id)
    if not profile:
        await update.effective_message.reply_text("Сначала /start — познакомимся, capisce? 🇮🇹")
        return ConversationHandler.END

    context.user_data["application"] = {}
    end_conversation(context, update, HOUSE_SEARCH_CONV)
    end_conversation(context, update, CALLBACK_CONV)
    context.user_data.pop("house_search", None)
    address = get_address(profile)

    await update.effective_message.reply_text(
        f"Fantastico, {address}! Оформляем заявку с {BOT_NAME} ✨🇮🇹\n\n"
        "Сначала ID дома — кнопка «🏠 Подобрать дом» или /houses.\n"
        "Напишите ID (например, house-001) или «отмена».",
        reply_markup=remove_reply_keyboard,
    )
    return APPLY_PROPERTY


async def apply_property(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text(
            f"Arrivederci, {address}! Заявка отменена 🇮🇹 alla grande в другой раз! 😊",
            reply_markup=inline_main_menu_keyboard(),
        )
        return ConversationHandler.END

    properties = load_properties()
    item = find_property_by_id(properties, text)
    if not item:
        await update.message.reply_text(
            f"Mamma mia, {address}, такого ID нет! 😅\n"
            "Загляните в «🏠 Подобрать дом» и попробуйте снова, capisce?"
        )
        return APPLY_PROPERTY

    context.user_data.setdefault("application", {})
    context.user_data["application"]["property_id"] = item["id"]
    context.user_data["application"]["property_title"] = item["title"]

    if profile and profile.get("name"):
        context.user_data["application"]["full_name"] = profile["name"]
        await update.message.reply_text(
            f"Bellissimo, {address}! 🏡 {item['title']} ({item['id']}) — che bella cosa!\n\n"
            f"{apply_phone_prompt_text()}",
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
            reply_markup=inline_main_menu_keyboard(),
        )
        return ConversationHandler.END

    if len(text) < 2:
        await update.message.reply_text("Ehm… имя слишком короткое! ☕ Введите ещё раз 😄")
        return APPLY_NAME

    context.user_data["application"]["full_name"] = text
    await update.message.reply_text(
        f"{apply_phone_prompt_text()}",
    )
    return APPLY_PHONE


async def apply_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text(
            f"Arrivederci, {address}! Заявка отменена 🇮🇹",
            reply_markup=inline_main_menu_keyboard(),
        )
        return ConversationHandler.END

    ok, normalized, _error = normalize_ru_mobile_phone(text)
    if not ok:
        await update.message.reply_text(PHONE_INVALID_MESSAGE)
        return APPLY_PHONE

    context.user_data["application"]["phone"] = format_ru_mobile_phone(normalized)

    if context.user_data.get("application", {}).get("from_house"):
        await update.message.reply_text(CALLBACK_TIME_PROMPT)
        return APPLY_TIME

    await update.message.reply_text(
        "Perfetto! 🌟 Добавьте комментарий — даты, гостей, пожелания…\n"
        "Или «-», если комментария нет, ecco!"
    )
    return APPLY_COMMENT


async def apply_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        context.user_data.pop("application", None)
        await update.message.reply_text(
            f"Arrivederci, {address}! Заявка отменена 🇮🇹",
            reply_markup=inline_main_menu_keyboard(),
        )
        return ConversationHandler.END

    ok, error = validate_callback_time(text)
    if not ok:
        await update.message.reply_text(f"{address}, {error}")
        return APPLY_TIME

    context.user_data.setdefault("application", {})["preferred_time"] = text
    await update.message.reply_text(CALLBACK_SITUATION_PROMPT)
    return APPLY_SITUATION


async def apply_situation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        context.user_data.pop("application", None)
        await update.message.reply_text(
            f"Arrivederci, {address}! Заявка отменена 🇮🇹",
            reply_markup=inline_main_menu_keyboard(),
        )
        return ConversationHandler.END

    situation = "" if text == "-" else text
    app_data = context.user_data.get("application", {})
    user = update.effective_user
    full_name = app_data.get("full_name", profile.get("name", ""))
    phone = app_data.get("phone", "")
    preferred_time = app_data.get("preferred_time", "")
    property_id = app_data.get("property_id", "")
    property_title = app_data.get("property_title", "")

    await send_house_application_to_manager(
        context,
        user=user,
        full_name=full_name,
        address=address,
        phone=phone,
        property_id=property_id,
        property_title=property_title,
        preferred_time=preferred_time,
        situation=situation,
    )

    save_application(
        user_id=user.id,
        username=user.username,
        full_name=full_name,
        phone=phone,
        property_id=property_id,
        property_title=property_title,
        comment=f"Время: {preferred_time}. Сообщение: {situation or '—'}",
    )

    context.user_data.pop("application", None)
    await update.message.reply_text(
        house_application_accepted_text(address),
        parse_mode="Markdown",
        reply_markup=inline_main_menu_keyboard(),
    )
    await send_application_gift(update, profile)
    return ConversationHandler.END


async def apply_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        await update.message.reply_text(
            f"Arrivederci, {address}! Заявка отменена 🇮🇹",
            reply_markup=inline_main_menu_keyboard(),
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
        reply_markup=inline_main_menu_keyboard(),
    )
    await send_application_gift(update, profile)
    return ConversationHandler.END


async def callback_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    end_conversation(context, update, APPLY_CONV)
    end_conversation(context, update, HOUSE_SEARCH_CONV)
    context.user_data.pop("application", None)
    context.user_data.pop("house_search", None)
    context.user_data.pop("callback", None)

    profile = load_profile(context, update.effective_user.id)
    if not profile:
        await query.message.reply_text("Сначала /start — познакомимся, capisce? 🇮🇹")
        end_conversation(context, update, CALLBACK_CONV)
        return ConversationHandler.END

    address = get_address(profile)
    await query.message.reply_text(
        f"Perfetto, {address}! Закажите обратный звонок — перезвоним и поможем с выбором 📞\n\n"
        f"{CALLBACK_PHONE_PROMPT}",
    )
    set_conversation(context, update, CALLBACK_CONV, CALLBACK_PHONE)
    return CALLBACK_PHONE


async def callback_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        context.user_data.pop("callback", None)
        await update.message.reply_text(
            f"Va bene, {address}, отменено! 🇮🇹",
            reply_markup=inline_main_menu_keyboard(),
        )
        return ConversationHandler.END

    ok, normalized, _error = normalize_ru_mobile_phone(text)
    if not ok:
        await update.message.reply_text(PHONE_INVALID_MESSAGE)
        return CALLBACK_PHONE

    context.user_data["callback"] = {"phone": format_ru_mobile_phone(normalized)}
    await update.message.reply_text(CALLBACK_TIME_PROMPT)
    set_conversation(context, update, CALLBACK_CONV, CALLBACK_TIME)
    return CALLBACK_TIME


async def callback_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        context.user_data.pop("callback", None)
        await update.message.reply_text(
            f"Va bene, {address}, отменено! 🇮🇹",
            reply_markup=inline_main_menu_keyboard(),
        )
        return ConversationHandler.END

    ok, error = validate_callback_time(text)
    if not ok:
        await update.message.reply_text(f"{address}, {error}")
        return CALLBACK_TIME

    context.user_data.setdefault("callback", {})["preferred_time"] = text
    await update.message.reply_text(CALLBACK_SITUATION_PROMPT)
    set_conversation(context, update, CALLBACK_CONV, CALLBACK_SITUATION)
    return CALLBACK_SITUATION


async def callback_situation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)

    if text.lower() in CANCEL_WORDS:
        context.user_data.pop("callback", None)
        await update.message.reply_text(
            f"Va bene, {address}, отменено! 🇮🇹",
            reply_markup=inline_main_menu_keyboard(),
        )
        return ConversationHandler.END

    situation = "" if text == "-" else text
    callback_data = context.user_data.get("callback", {})
    phone = callback_data.get("phone", "")
    preferred_time = callback_data.get("preferred_time", "")
    user = update.effective_user
    full_name = profile.get("name", "") if profile else ""

    sent = await send_callback_request_to_manager(
        context,
        user=user,
        full_name=full_name,
        address=address,
        phone=phone,
        preferred_time=preferred_time,
        situation=situation,
    )

    save_application(
        user_id=user.id,
        username=user.username,
        full_name=full_name,
        phone=phone,
        property_id="callback",
        property_title="Обратный звонок",
        comment=f"Время: {preferred_time}. Ситуация: {situation or '—'}",
    )

    context.user_data.pop("callback", None)
    end_conversation(context, update, CALLBACK_CONV)

    if sent:
        confirm = (
            f"Grazie, {address}! Заявка на обратный звонок принята ✅\n"
            f"Перезвоним на {phone} — {preferred_time}.\n"
            f"{BOT_NAME} уже передал заявку менеджеру! 📞🇮🇹"
        )
    else:
        confirm = (
            f"Grazie, {address}! Заявку записал ✅\n"
            f"Перезвоним на {phone} — {preferred_time}.\n"
            "Если менеджер не свяжется — позвоните нам: "
            f"{get_company_phone()}"
        )

    await update.message.reply_text(confirm, reply_markup=inline_main_menu_keyboard())
    return ConversationHandler.END


async def callback_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    end_conversation(context, update, CALLBACK_CONV)
    return await cancel(update, context)


async def start_and_end_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    end_conversation(context, update, CALLBACK_CONV)
    await start(update, context)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("application", None)
    clear_onboarding(context)
    profile = load_profile(context, update.effective_user.id)
    address = get_address(profile)
    await update.message.reply_text(
        f"Va bene, {address}, отменено! 🇮🇹 {BOT_NAME} всегда здесь! 😊",
        reply_markup=inline_main_menu_keyboard(),
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

    app = (
        Application.builder()
        .token(token)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .post_init(warmup_assistant)
        .build()
    )

    house_search_handler = ConversationHandler(
        entry_points=[
            CommandHandler("houses", houses_start),
            CallbackQueryHandler(houses_start, pattern=f"^{re.escape(MENU_HOUSES)}$"),
        ],
        states={
            HOUSE_REGION: [
                CallbackQueryHandler(house_region_chosen, pattern=f"^{re.escape(SEARCH_REGION_PREFIX)}"),
                CallbackQueryHandler(house_search_cancel_callback, pattern=f"^{re.escape(SEARCH_CANCEL)}$"),
            ],
            HOUSE_GUESTS: [
                CallbackQueryHandler(house_guests_chosen, pattern=f"^{re.escape(SEARCH_GUESTS_PREFIX)}"),
                CallbackQueryHandler(house_search_cancel_callback, pattern=f"^{re.escape(SEARCH_CANCEL)}$"),
            ],
            HOUSE_BUDGET: [
                CallbackQueryHandler(house_budget_chosen, pattern=f"^{re.escape(SEARCH_BUDGET_PREFIX)}"),
                CallbackQueryHandler(house_search_cancel_callback, pattern=f"^{re.escape(SEARCH_CANCEL)}$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", house_search_cancel),
            CommandHandler("start", house_search_end_start),
        ],
        name=HOUSE_SEARCH_CONV,
    )

    callback_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback_start, pattern=f"^{re.escape(MENU_CALLBACK)}$"),
        ],
        states={
            CALLBACK_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, callback_phone),
            ],
            CALLBACK_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, callback_time),
            ],
            CALLBACK_SITUATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, callback_situation),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", callback_cancel),
            CommandHandler("start", start_and_end_callback),
        ],
        name=CALLBACK_CONV,
    )

    apply_handler = ConversationHandler(
        entry_points=[
            CommandHandler("apply", apply_start),
            CallbackQueryHandler(apply_start, pattern=f"^{re.escape(MENU_APPLY)}$"),
            CallbackQueryHandler(apply_from_house, pattern=f"^{re.escape(HOUSE_APPLY_PREFIX)}"),
            MessageHandler(
                filters.Regex(re.compile(r"(оформить\s+заявку|оставить\s+заявку|хочу\s+аренд)", re.I)),
                apply_start,
            ),
        ],
        states={
            APPLY_PROPERTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_property)],
            APPLY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_name)],
            APPLY_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_phone)],
            APPLY_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_time)],
            APPLY_SITUATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_situation)],
            APPLY_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_comment)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start_and_end_apply),
        ],
        name=APPLY_CONV,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(onboard_gender, pattern=r"^gender:"))
    app.add_handler(house_search_handler)
    app.add_handler(CallbackQueryHandler(house_show_details, pattern=f"^{re.escape(HOUSE_PICK_PREFIX)}"))
    app.add_handler(callback_handler)
    app.add_handler(apply_handler)
    app.add_handler(
        CallbackQueryHandler(callback_start, pattern=f"^{re.escape(MENU_CALLBACK)}$")
    )
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text))
    app.add_error_handler(on_error)

    return app


def main() -> None:
    application = build_application()
    logger.info("%s запущен. Нажмите Ctrl+C для остановки.", BOT_NAME)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
