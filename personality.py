"""Персона бота — Джонни Рентино."""

from __future__ import annotations

from typing import Any

BOT_NAME = "Джонни Рентино"

GENDER_MALE = "male"
GENDER_FEMALE = "female"
GENDER_NEUTRAL = "neutral"


def get_honorific(gender: str) -> str:
    mapping = {
        GENDER_MALE: "сеньор",
        GENDER_FEMALE: "сеньорита",
        GENDER_NEUTRAL: "caro amico",
    }
    return mapping.get(gender, "caro amico")


def get_address(profile: dict[str, Any] | None) -> str:
    if not profile:
        return "caro amico"
    name = profile.get("name", "").strip()
    gender = profile.get("gender", GENDER_NEUTRAL)
    honorific = get_honorific(gender)
    if gender == GENDER_NEUTRAL:
        return name or honorific
    if name:
        return f"{honorific} {name}"
    return honorific


def get_rag_client_context(profile: dict[str, Any] | None) -> str:
    if not profile:
        return ""
    name = profile.get("name", "").strip()
    gender = profile.get("gender", GENDER_NEUTRAL)
    honorific = get_honorific(gender)
    lines = [
        "Данные о клиенте (используй для обращения):",
        f"- Имя: {name or 'не указано'}",
        f"- Обращение: {honorific}",
    ]
    if gender == GENDER_MALE:
        lines.append("- Используй только «сеньор», не «сеньорита».")
    elif gender == GENDER_FEMALE:
        lines.append("- Используй только «сеньорита», не «сеньор».")
    else:
        lines.append("- Обращайся по имени или «caro amico», без сеньор/сеньорита.")
    return "\n".join(lines)
