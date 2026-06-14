from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import APPLICATIONS_FILE


def _ensure_file() -> None:
    APPLICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not APPLICATIONS_FILE.exists():
        APPLICATIONS_FILE.write_text("[]", encoding="utf-8")


def load_applications() -> list[dict[str, Any]]:
    _ensure_file()
    with APPLICATIONS_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def save_application(
    *,
    user_id: int,
    username: str | None,
    full_name: str,
    phone: str,
    property_id: str,
    property_title: str,
    comment: str = "",
) -> dict[str, Any]:
    record = {
        "id": str(uuid.uuid4())[:8],
        "user_id": user_id,
        "username": username or "",
        "full_name": full_name.strip(),
        "phone": phone.strip(),
        "property_id": property_id.strip(),
        "property_title": property_title.strip(),
        "comment": comment.strip(),
        "status": "new",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    items = load_applications()
    items.append(record)
    APPLICATIONS_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record
