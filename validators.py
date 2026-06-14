from __future__ import annotations

import re

# Российский мобильный: +7/7/8 → 9 → ещё 9 цифр (итого 11 цифр: 79XXXXXXXXX)
_RU_PHONE_ALLOWED = re.compile(r"^[\d\s+\-().]+$")
_RU_PHONE_DIGITS = re.compile(r"^79\d{9}$")

_TIME_WITH_COLON = re.compile(r"\d{1,2}[:\.]\d{2}")
_TIME_RANGE = re.compile(r"\d{1,2}\s*[-–—]\s*\d{1,2}")
_DAY_WORDS = (
    "сегодня",
    "завтра",
    "послезавтра",
    "утром",
    "днём",
    "днем",
    "вечером",
    "ночью",
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
    "пн",
    "вт",
    "ср",
    "чт",
    "пт",
    "сб",
    "вс",
)
_TIME_CONTEXT = ("после", "до", "между", "около", "примерно", " в ", "с ", "до ")

PHONE_INVALID_MESSAGE = "Телефон указан неверно. Введите номер повторно"


def normalize_ru_mobile_phone(text: str) -> tuple[bool, str, str]:
    """
    Проверка российского мобильного номера.
    Возвращает (ok, нормализованный +7XXXXXXXXXX, текст ошибки).
    """
    raw = (text or "").strip()
    if not raw:
        return False, "", PHONE_INVALID_MESSAGE

    if re.search(r"[a-zA-Zа-яА-ЯёЁ]", raw):
        return False, "", PHONE_INVALID_MESSAGE

    if not _RU_PHONE_ALLOWED.match(raw):
        return False, "", PHONE_INVALID_MESSAGE

    digits = re.sub(r"\D", "", raw)
    if digits.startswith("8"):
        digits = "7" + digits[1:]

    if not digits.startswith("7"):
        return False, "", PHONE_INVALID_MESSAGE

    if len(digits) != 11:
        return False, "", PHONE_INVALID_MESSAGE

    if digits[1] != "9":
        return False, "", PHONE_INVALID_MESSAGE

    if not _RU_PHONE_DIGITS.match(digits):
        return False, "", PHONE_INVALID_MESSAGE

    return True, f"+{digits}", ""


def format_ru_mobile_phone(normalized: str) -> str:
    """+79038417000 → +7 903 841 7000"""
    digits = re.sub(r"\D", "", normalized)
    if len(digits) != 11:
        return normalized
    return f"+7 {digits[1:4]} {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"


def validate_callback_time(text: str) -> tuple[bool, str]:
    """Проверка поля «удобное время» для обратного звонка."""
    raw = (text or "").strip()
    if len(raw) < 5:
        return False, "Ehm… напишите подробнее, capisce? 🕐\nНапример: «завтра после 18:00»"

    lower = raw.lower()

    if re.fullmatch(r"\d{1,4}", lower):
        return False, "Так не поймём 🕐\nНапример: «сегодня в 15:00» или «завтра с 10 до 12»"

    has_colon_time = bool(_TIME_WITH_COLON.search(lower))
    has_range = bool(_TIME_RANGE.search(lower))
    has_day = any(word in lower for word in _DAY_WORDS)
    has_context = any(word in lower for word in _TIME_CONTEXT)
    has_hour = bool(re.search(r"\b([01]?\d|2[0-3])\b", lower))

    if has_colon_time or has_range:
        return True, ""

    if has_day and (has_hour or has_context or has_range):
        return True, ""

    if has_day and len(lower.split()) >= 2:
        return True, ""

    return False, (
        "Не похоже на время звонка 🕐\n"
        "Например: «сегодня после 18:00», «завтра утром», «в пятницу с 14 до 16»"
    )
