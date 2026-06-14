from __future__ import annotations

from telegram import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove

from config import get_company_phone

BTN_HOUSES = "🏠 Подобрать casa"
BTN_APPLY = "✨ Оформить заявку"
BTN_CALLBACK = "📞 Перезвоните мне"

MENU_HOUSES = "menu:houses"
MENU_APPLY = "menu:apply"
MENU_CALLBACK = "menu:callback"

GENDER_MALE = "gender:male"
GENDER_FEMALE = "gender:female"
GENDER_NEUTRAL = "gender:neutral"

SEARCH_REGION_PREFIX = "search:region:"
SEARCH_GUESTS_PREFIX = "search:guests:"
SEARCH_BUDGET_PREFIX = "search:budget:"
SEARCH_CANCEL = "search:cancel"

HOUSE_PICK_PREFIX = "house:pick:"
HOUSE_APPLY_PREFIX = "house:apply:"

BTN_CANCEL = "❌ Annulla"
BTN_APPLY_HERO = "✨ Оформить заявку — perfetto!"

remove_reply_keyboard = ReplyKeyboardRemove()

_TELEGRAM_BUTTON_LIMIT = 64


def _truncate(text: str, max_len: int = _TELEGRAM_BUTTON_LIMIT) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def property_pick_label(item: dict) -> str:
    title = item.get("title") or item.get("id", "Дом")
    return _truncate(f"🏡 {title}")


def call_company_button() -> InlineKeyboardButton:
    phone = get_company_phone()
    return InlineKeyboardButton(
        _truncate(f"☎️ {phone} — скопировать"),
        copy_text=CopyTextButton(text=phone),
    )


def menu_navigation_row() -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(BTN_HOUSES, callback_data=MENU_HOUSES),
        InlineKeyboardButton(BTN_CALLBACK, callback_data=MENU_CALLBACK),
    ]


def inline_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            menu_navigation_row(),
            [call_company_button()],
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


def house_search_region_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🌊 Mare — у моря", callback_data=f"{SEARCH_REGION_PREFIX}sea")],
            [
                InlineKeyboardButton("🏡 Подмосковье", callback_data=f"{SEARCH_REGION_PREFIX}moscow"),
                InlineKeyboardButton("☀️ Краснодар", callback_data=f"{SEARCH_REGION_PREFIX}krasnodar"),
            ],
            [
                InlineKeyboardButton("🏖 Крым", callback_data=f"{SEARCH_REGION_PREFIX}crimea"),
                InlineKeyboardButton("🌍 Ovunque — любой", callback_data=f"{SEARCH_REGION_PREFIX}any"),
            ],
            [InlineKeyboardButton(BTN_CANCEL, callback_data=SEARCH_CANCEL)],
        ]
    )


def house_search_guests_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👫 2–3", callback_data=f"{SEARCH_GUESTS_PREFIX}2-3"),
                InlineKeyboardButton("👨‍👩‍👧 4–6", callback_data=f"{SEARCH_GUESTS_PREFIX}4-6"),
            ],
            [
                InlineKeyboardButton("🏠 7–10", callback_data=f"{SEARCH_GUESTS_PREFIX}7-10"),
                InlineKeyboardButton("🎉 11+", callback_data=f"{SEARCH_GUESTS_PREFIX}11+"),
            ],
            [InlineKeyboardButton("🤷 Qualsiasi — любое", callback_data=f"{SEARCH_GUESTS_PREFIX}any")],
            [InlineKeyboardButton(BTN_CANCEL, callback_data=SEARCH_CANCEL)],
        ]
    )


def house_search_budget_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💸 до 50k ₽", callback_data=f"{SEARCH_BUDGET_PREFIX}50000"),
                InlineKeyboardButton("💸 до 100k ₽", callback_data=f"{SEARCH_BUDGET_PREFIX}100000"),
            ],
            [
                InlineKeyboardButton("💎 до 150k ₽", callback_data=f"{SEARCH_BUDGET_PREFIX}150000"),
                InlineKeyboardButton("💎 до 200k ₽", callback_data=f"{SEARCH_BUDGET_PREFIX}200000"),
            ],
            [InlineKeyboardButton("♾ Senza limite", callback_data=f"{SEARCH_BUDGET_PREFIX}any")],
            [InlineKeyboardButton(BTN_CANCEL, callback_data=SEARCH_CANCEL)],
        ]
    )


def house_search_results_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for item in items:
        prop_id = item["id"]
        row.append(
            InlineKeyboardButton(
                property_pick_label(item),
                callback_data=f"{HOUSE_PICK_PREFIX}{prop_id}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(menu_navigation_row())
    rows.append([call_company_button()])
    return InlineKeyboardMarkup(rows)


def house_detail_keyboard(property_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    BTN_APPLY_HERO,
                    callback_data=f"{HOUSE_APPLY_PREFIX}{property_id}",
                )
            ],
            menu_navigation_row(),
            [call_company_button()],
        ]
    )
