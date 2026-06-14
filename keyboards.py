from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

BTN_HOUSES = "🏠 Список домов"
BTN_APPLY = "✨ Оформить заявку"
BTN_HELP = "❓ Помощь"
BTN_PROFILE = "👤 Мой профиль"

GENDER_MALE = "gender:male"
GENDER_FEMALE = "gender:female"
GENDER_NEUTRAL = "gender:neutral"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_HOUSES), KeyboardButton(BTN_APPLY)],
            [KeyboardButton(BTN_HELP), KeyboardButton(BTN_PROFILE)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Спросите про дом или нажмите кнопку…",
    )


def gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👨 Сеньор", callback_data=GENDER_MALE),
                InlineKeyboardButton("👩 Сеньорита", callback_data=GENDER_FEMALE),
            ],
            [InlineKeyboardButton("🤝 Просто по имени", callback_data=GENDER_NEUTRAL)],
        ]
    )
