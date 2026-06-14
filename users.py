from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import USERS_FILE


def _load_all() -> dict[str, Any]:
    if not USERS_FILE.exists():
        return {"users": {}}
    with USERS_FILE.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        return {"users": {}}
    data.setdefault("users", {})
    return data


def _save_all(data: dict[str, Any]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with USERS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_user_profile(user_id: int) -> dict[str, Any] | None:
    data = _load_all()
    profile = data["users"].get(str(user_id))
    if not profile or not profile.get("name"):
        return None
    return profile


def save_user_profile(
    user_id: int,
    *,
    name: str,
    gender: str,
    username: str | None = None,
) -> dict[str, Any]:
    data = _load_all()
    profile = {
        "name": name.strip(),
        "gender": gender,
        "username": username,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    data["users"][str(user_id)] = profile
    _save_all(data)
    return profile
