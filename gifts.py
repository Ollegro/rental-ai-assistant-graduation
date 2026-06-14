"""Подарок после разговора — ссылка на профиль Suno."""
from __future__ import annotations

import re

from config import SUNO_PROFILE_URL
from personality import BOT_NAME

ALBUM_NAME = "Свинг Бантидос"

FAREWELL_RE = re.compile(
    r"(?:"
    r"спасибо|благодарю|пока|до\s+свидания|до\s+встречи|всё|все|хватит|"
    r"ciao|arrivederci|grazie|goodbye|bye|на\s+сегодня|закончим|"
    r"больше\s+не\s+нужно|вопросов\s+нет"
    r")",
    re.I,
)


def is_farewell(text: str) -> bool:
    return bool(FAREWELL_RE.search(text.strip()))


def format_gift_message() -> str:
    return (
        f"🎁 Подарок от {BOT_NAME} — альбом «{ALBUM_NAME}»:\n\n"
        "В подарок выберите песню для прослушивания 🎵\n"
        f"{SUNO_PROFILE_URL}\n\n"
        "Alla grande! Приятного прослушивания ☀️"
    )
