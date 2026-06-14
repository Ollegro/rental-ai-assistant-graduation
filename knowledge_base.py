from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import PROPERTIES_FILE


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
    return (
        f"ID: {item['id']}\n"
        f"Название: {item['title']}\n"
        f"Тип: {item.get('house_type', 'дом')}\n"
        f"Локация: {item['location']}\n"
        f"Цена: {item['price_per_month']} {item.get('currency', 'RUB')} в месяц\n"
        f"Комнаты: {item.get('bedrooms', '?')}, санузлы: {item.get('bathrooms', '?')}\n"
        f"Площадь: {item.get('area_sqm', '?')} кв.м\n"
        f"Минимальный срок аренды: {item.get('min_rent_months', 1)} мес.\n"
        f"Доступен с: {item.get('available_from', 'уточняется')}\n"
        f"Животные: {pets}\n"
        f"Удобства: {amenities}\n"
        f"Описание: {item.get('description', '')}"
    )


def format_properties_summary(properties: list[dict[str, Any]]) -> str:
    lines = ["Доступные объекты:\n"]
    for item in properties:
        lines.append(
            f"• {item['id']} — {item['title']} ({item['location']}), "
            f"{item['price_per_month']} ₽/мес."
        )
    return "\n".join(lines)


def find_property_by_id(properties: list[dict[str, Any]], property_id: str) -> dict[str, Any] | None:
    normalized = property_id.strip().lower()
    for item in properties:
        if item["id"].lower() == normalized:
            return item
    return None
