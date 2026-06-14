"""
Скачать реалистичные фото домов (Unsplash, бесплатная лицензия) и разложить по объектам.

Прямой парсинг Циан/Авито не используем: нарушает правила площадок и авторские права.
Для тестового проекта — стоковые фото в стиле объявлений об аренде.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import PHOTOS_DIR, PROPERTIES_FILE  # noqa: E402

# Unsplash — проверенные ID (https://unsplash.com/license)
STOCK_PHOTOS = [
    "photo-1564013799919-ab600027ffc6",
    "photo-1600585154340-be6161a56a0c",
    "photo-1600566753190-17f0baa2a6c3",
    "photo-1600607687644-c7171b42498f",
    "photo-1600585154526-990dced4db0d",
    "photo-1502672260266-1c1ef2d93688",
    "photo-1522708323590-d24dbb6b0267",
    "photo-1570129477492-45c003edd2be",
    "photo-1600585152915-d208bec867a1",
    "photo-1616486338812-3dadae4b4ace",
    "photo-1600210492486-724fe5c67fb0",
    "photo-1513584684374-8bab748fbf90",
    "photo-1600566752355-35792bedcfea",
    "photo-1600607688969-a5bfcd646154",
]

WIDTH, HEIGHT = 960, 640
USER_AGENT = "RentalBotGraduationProject/1.0 (educational)"


def unsplash_url(photo_id: str) -> str:
    return f"https://images.unsplash.com/{photo_id}?w={WIDTH}&h={HEIGHT}&fit=crop&q=80&auto=format"


def download_image(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def save_jpeg(data: bytes, path: Path) -> None:
    image = Image.open(BytesIO(data))
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "JPEG", quality=85, optimize=True)


def photo_count(property_index: int) -> int:
    return 4 if property_index % 2 == 0 else 3


def pick_indices(property_id: str, count: int, pool_size: int) -> list[int]:
    digest = hashlib.md5(property_id.encode()).hexdigest()
    start = int(digest[:8], 16) % pool_size
    return [(start + offset) % pool_size for offset in range(count)]


def build_pool(pool_dir: Path) -> list[Path]:
    pool_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for index, photo_id in enumerate(STOCK_PHOTOS, 1):
        path = pool_dir / f"{index:03d}.jpg"
        if path.is_file() and path.stat().st_size > 10_000:
            paths.append(path)
            continue
        url = unsplash_url(photo_id)
        try:
            save_jpeg(download_image(url), path)
            paths.append(path)
            print(f"  pool {index}/{len(STOCK_PHOTOS)} OK")
            time.sleep(0.15)
        except (urllib.error.URLError, OSError, Image.UnidentifiedImageError) as exc:
            print(f"  skip {photo_id}: {exc}")

    return paths


def main() -> int:
    pool_dir = ROOT / "data" / "photo_pool"
    print("Скачиваем стоковые фото (Unsplash)...")
    pool = build_pool(pool_dir)
    if len(pool) < 8:
        print("Ошибка: мало фото в пуле. Проверьте интернет.", file=sys.stderr)
        return 1

    with PROPERTIES_FILE.open(encoding="utf-8") as file:
        properties = json.load(file)

    assigned = 0
    for prop_index, item in enumerate(properties):
        property_id = item["id"]
        count = photo_count(prop_index)
        indices = pick_indices(property_id, count, len(pool))
        folder = PHOTOS_DIR / property_id
        folder.mkdir(parents=True, exist_ok=True)

        names: list[str] = []
        for photo_num, pool_index in enumerate(indices, 1):
            name = f"{photo_num:02d}.jpg"
            shutil.copy2(pool[pool_index], folder / name)
            names.append(name)
            assigned += 1
        item["photos"] = names

    with PROPERTIES_FILE.open("w", encoding="utf-8") as file:
        json.dump(properties, file, ensure_ascii=False, indent=2)
        file.write("\n")

    size_mb = sum(f.stat().st_size for f in PHOTOS_DIR.rglob("*.jpg")) / (1024 * 1024)
    print(f"OK: {len(properties)} домов, {assigned} фото, {size_mb:.1f} MB, пул {len(pool)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
