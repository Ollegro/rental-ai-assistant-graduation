from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
PROMPTS_DIR = ROOT_DIR / "prompts"
PROPERTIES_FILE = DATA_DIR / "properties.json"
APPLICATIONS_FILE = DATA_DIR / "applications.json"
USERS_FILE = DATA_DIR / "users.json"
SUNO_PROFILE_URL = "https://suno.com/@lego_1"
SYSTEM_PROMPT_FILE = PROMPTS_DIR / "system.txt"


def get_faiss_dir() -> Path:
    """FAISS на Windows не пишет в пути с кириллицей — используем ASCII-кэш."""
    custom = os.getenv("FAISS_DIR", "").strip()
    if custom:
        return Path(custom)
    if os.name == "nt":
        local_app = os.getenv("LOCALAPPDATA", str(Path.home()))
        return Path(local_app) / "rental-ai-assistant" / "faiss_index"
    return DATA_DIR / "faiss_index"


FAISS_DIR = get_faiss_dir()

PLACEHOLDER_KEYS = {
    "",
    "sk-ваш-ключ-openai",
    "ваш_ключ_proxyapi",
    "твой API-ключ",
    "ваш-ключ-proxyapi",
    "ваш_токен_от_BotFather",
}


def get_api_key() -> str | None:
    for name in ("OPENAI_API_KEY", "PROXYAPI_KEY", "API_KEY"):
        value = os.getenv(name, "").strip()
        if value and value not in PLACEHOLDER_KEYS:
            return value
    return None


def get_base_url() -> str:
    for name in ("OPENAI_API_BASE", "PROXYAPI_BASE_URL"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return "https://api.proxyapi.ru/openai/v1"


def get_chat_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def get_bot_token() -> str | None:
    value = os.getenv("BOT_TOKEN", "").strip()
    if value and value not in PLACEHOLDER_KEYS:
        return value
    return None


def load_system_prompt() -> str:
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
