from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import PROPERTIES_FILE
from personality import BOT_NAME


def load_properties(path: Path | None = None) -> list[dict[str, Any]]:
    source = path or PROPERTIES_FILE
    with source.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("properties.json должен содержать массив объектов")
    return data


def property_to_text(item: dict[str, Any]) -> str:
    amenities = ", ".join(item.get("amenities", []))
    pets = "можно" if item.get("pets_allowed") else "нельзя"
    has_pool = "да" if "бассейн" in item.get("amenities", []) else "нет"
    has_sauna = "да" if "сауна" in item.get("amenities", []) else "нет"

    if item.get("near_sea"):
        sea_line = item.get("sea_line")
        sea_info = f"У моря: да, линия {sea_line}"
    else:
        sea_info = "У моря: нет"

    return (
        f"ID: {item['id']}\n"
        f"Название: {item['title']}\n"
        f"Тип: {item.get('house_type', 'дом')}\n"
        f"Локация: {item['location']}\n"
        f"{sea_info}\n"
        f"Вместимость: {item.get('capacity_min', '?')}–{item.get('capacity_max', '?')} человек "
        f"({item.get('capacity_label', 'не указано')})\n"
        f"Цена: {item['price_per_month']} {item.get('currency', 'RUB')} в месяц\n"
        f"Комнаты: {item.get('bedrooms', '?')}, санузлы: {item.get('bathrooms', '?')}\n"
        f"Площадь: {item.get('area_sqm', '?')} кв.м\n"
        f"Минимальный срок аренды: {item.get('min_rent_months', 1)} мес.\n"
        f"Доступен с: {item.get('available_from', 'уточняется')}\n"
        f"Животные: {pets}\n"
        f"Бассейн: {has_pool}, сауна: {has_sauna}\n"
        f"Удобства: {amenities}\n"
        f"Описание: {item.get('description', '')}"
    )


TELEGRAM_MESSAGE_LIMIT = 4000


def format_property_line(item: dict[str, Any]) -> str:
    return (
        f"• {item['id']} — {item['title']} ({item['location']}), "
        f"{item.get('capacity_label', '?')}, {item['price_per_month']} ₽/мес."
    )


def split_text_for_telegram(text: str, max_len: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n"):
        block = paragraph if not current else f"{current}\n{paragraph}"
        if len(block) <= max_len:
            current = block
            continue

        if current:
            chunks.append(current)
            current = ""

        while len(paragraph) > max_len:
            chunks.append(paragraph[:max_len])
            paragraph = paragraph[max_len:]

        current = paragraph

    if current:
        chunks.append(current)
    return chunks


def format_properties_summary(properties: list[dict[str, Any]]) -> str:
    header = (
        f"🏡 Ecco! Список домов от {BOT_NAME} ({len(properties)} шт.), alla grande:\n"
    )
    lines = [format_property_line(item) for item in properties]
    return header + "\n".join(lines)


def format_properties_summary_messages(properties: list[dict[str, Any]]) -> list[str]:
    if not properties:
        return ["Список объектов пока пуст."]

    header = f"🏡 Ecco! Список домов от {BOT_NAME} ({len(properties)} шт.), alla grande:"
    lines = [format_property_line(item) for item in properties]

    messages: list[str] = []
    current = header
    for index, line in enumerate(lines):
        candidate = f"{current}\n{line}"
        if len(candidate) <= TELEGRAM_MESSAGE_LIMIT:
            current = candidate
            continue

        messages.append(current)
        continuation = f"🇮🇹 Ancora case! (продолжение {len(messages) + 1})"
        current = f"{continuation}\n{line}"

    if current:
        messages.append(current)
    return messages


def find_property_by_id(properties: list[dict[str, Any]], property_id: str) -> dict[str, Any] | None:
    normalized = property_id.strip().lower()
    for item in properties:
        if item["id"].lower() == normalized:
            return item
    return None
