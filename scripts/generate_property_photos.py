"""Сгенерировать 3–4 placeholder-фото для каждого дома в data/photos/."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import PHOTOS_DIR, PROPERTIES_FILE  # noqa: E402

WIDTH, HEIGHT = 960, 640
SCENES = ("фасад", "гостиная", "спальня", "терраса")


def _colors(seed: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    digest = hashlib.md5(seed.encode()).hexdigest()
    c1 = tuple(int(digest[i : i + 2], 16) for i in (0, 2, 4))
    c2 = tuple(int(digest[i : i + 2], 16) for i in (6, 8, 10))
    return c1, c2


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_photo(
    *,
    property_id: str,
    title: str,
    location: str,
    scene: str,
    index: int,
) -> Image.Image:
    c1, c2 = _colors(f"{property_id}-{index}")
    image = Image.new("RGB", (WIDTH, HEIGHT), c1)
    draw = ImageDraw.Draw(image)

    for y in range(HEIGHT):
        ratio = y / HEIGHT
        color = tuple(int(c1[i] * (1 - ratio) + c2[i] * ratio) for i in range(3))
        draw.line([(0, y), (WIDTH, y)], fill=color)

    draw.rectangle([40, 40, WIDTH - 40, HEIGHT - 40], outline=(255, 255, 255), width=3)
    draw.text((60, 70), property_id, fill=(255, 255, 255), font=_font(42))
    draw.text((60, 130), title[:48], fill=(255, 255, 255), font=_font(28))
    draw.text((60, 180), location[:52], fill=(230, 230, 230), font=_font(22))
    draw.text((60, HEIGHT - 100), f"Фото: {scene}", fill=(255, 255, 255), font=_font(30))
    draw.text((60, HEIGHT - 55), "Rental AI · placeholder", fill=(200, 200, 200), font=_font(18))
    return image


def photo_count_for_index(index: int) -> int:
    return 4 if index % 2 == 0 else 3


def main() -> int:
    with PROPERTIES_FILE.open(encoding="utf-8") as file:
        properties = json.load(file)

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    total_files = 0

    for index, item in enumerate(properties):
        property_id = item["id"]
        count = photo_count_for_index(index)
        folder = PHOTOS_DIR / property_id
        folder.mkdir(parents=True, exist_ok=True)

        names: list[str] = []
        for photo_index in range(count):
            name = f"{photo_index + 1:02d}.jpg"
            path = folder / name
            scene = SCENES[photo_index % len(SCENES)]
            image = render_photo(
                property_id=property_id,
                title=item.get("title", property_id),
                location=item.get("location", ""),
                scene=scene,
                index=photo_index,
            )
            image.save(path, "JPEG", quality=82, optimize=True)
            names.append(name)
            total_files += 1

        item["photos"] = names

    with PROPERTIES_FILE.open("w", encoding="utf-8") as file:
        json.dump(properties, file, ensure_ascii=False, indent=2)
        file.write("\n")

    size_mb = sum(f.stat().st_size for f in PHOTOS_DIR.rglob("*.jpg")) / (1024 * 1024)
    print(f"OK: {len(properties)} домов, {total_files} фото, {size_mb:.1f} MB в {PHOTOS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
