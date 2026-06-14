"""Сборка или пересборка FAISS-индекса базы знаний."""
from __future__ import annotations

import argparse

from rag import build_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Построить FAISS-индекс объектов аренды")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Удалить существующий индекс и пересобрать заново",
    )
    args = parser.parse_args()

    path = build_index(force=args.force)
    print(f"Индекс сохранён: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
