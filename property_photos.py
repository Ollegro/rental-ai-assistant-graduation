"""Фотографии объектов аренды."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from config import PHOTOS_DIR

PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
MAX_PHOTOS_IN_ALBUM = 10


def get_property_photo_dir(property_id: str) -> Path:
    return PHOTOS_DIR / property_id


def get_property_photo_paths(item: dict[str, Any]) -> list[Path]:
    property_id = item.get("id", "")
    if not property_id:
        return []

    folder = get_property_photo_dir(property_id)
    listed = item.get("photos")
    if isinstance(listed, list) and listed:
        paths: list[Path] = []
        for name in listed:
            path = folder / str(name)
            if path.is_file():
                paths.append(path)
        return paths[:MAX_PHOTOS_IN_ALBUM]

    if not folder.is_dir():
        return []

    files: list[Path] = []
    for ext in PHOTO_EXTENSIONS:
        files.extend(folder.glob(f"*{ext}"))
    return sorted(files)[:MAX_PHOTOS_IN_ALBUM]


def property_photo_caption(item: dict[str, Any]) -> str:
    price = f"{int(item['price_per_month']):,}".replace(",", " ")
    return (
        f"🏡 {item['title']} ({item['id']})\n"
        f"📍 {item.get('location', '—')}\n"
        f"👥 {item.get('capacity_label', '?')} · 💰 {price} ₽/мес"
    )
