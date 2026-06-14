from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove

BTN_HOUSES = "🏠 Список домов"
BTN_APPLY = "✨ Оформить заявку"
BTN_HELP = "❓ Помощь"
BTN_PROFILE = "👤 Мой профиль"

MENU_HOUSES = "menu:houses"
MENU_APPLY = "menu:apply"
MENU_HELP = "menu:help"
MENU_PROFILE = "menu:profile"

GENDER_MALE = "gender:male"
GENDER_FEMALE = "gender:female"
GENDER_NEUTRAL = "gender:neutral"

remove_reply_keyboard = ReplyKeyboardRemove()


def inline_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(BTN_HOUSES, callback_data=MENU_HOUSES),
                InlineKeyboardButton(BTN_APPLY, callback_data=MENU_APPLY),
            ],
            [
                InlineKeyboardButton(BTN_HELP, callback_data=MENU_HELP),
                InlineKeyboardButton(BTN_PROFILE, callback_data=MENU_PROFILE),
            ],
        ]
    )


def unisex_gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👨 Сеньор", callback_data=GENDER_MALE),
                InlineKeyboardButton("👩 Сеньорита", callback_data=GENDER_FEMALE),
            ],
        ]
    )
