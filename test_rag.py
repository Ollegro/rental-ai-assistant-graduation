"""Локальный тест RAG без Telegram."""
from __future__ import annotations

import sys

from rag import RentalAssistant


def main() -> int:
    questions = [
        "Какие дома доступны у моря?",
        "Нужен дом до 60000 рублей с животными",
        "Расскажи про виллу на Новой Риге",
    ]

    if len(sys.argv) > 1:
        questions = [" ".join(sys.argv[1:])]

    assistant = RentalAssistant()

    for question in questions:
        print("\n" + "=" * 60)
        print(f"Вопрос: {question}")
        print("-" * 60)
        print(assistant.answer(question))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
