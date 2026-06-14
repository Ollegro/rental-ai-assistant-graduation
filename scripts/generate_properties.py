"""Генерация 50 разнообразных объектов аренды для data/properties.json."""
from __future__ import annotations

import json
import random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "properties.json"

INLAND = [
    "Московская область, Истра",
    "Московская область, Дмитров",
    "Московская область, Новая Рига",
    "Московская область, Руза",
    "Московская область, Пушкино",
    "Ленинградская область, Выборг",
    "Ленинградская область, Всеволожск",
    "Тверская область, Торжок",
    "Тверская область, Конаково",
    "Республика Карелия, Сортавала",
    "Нижегородская область, Павлово",
    "Владимирская область, Суздаль",
    "Калужская область, Таруса",
    "Ярославская область, Рыбинск",
    "Рязанская область, Касимов",
]

SEA_REGIONS = [
    ("Краснодарский край", ["Сочи", "Геленджик", "Анапа", "Туапсе"]),
    ("Крым", ["Ялта", "Евпатория", "Феодосия", "Алушта"]),
]

BASE_AMENITIES = ["парковка", "Wi-Fi"]
EXTRA_AMENITIES = [
    "камин",
    "терраса",
    "мангал",
    "кондиционер",
    "рабочий кабинет",
    "детская площадка",
    "охрана",
    "спортзал",
    "бильярд",
    "большая гостиная",
]

CAPACITY_PROFILES = {
    "2-3": {
        "label": "2–3 человека",
        "capacity_min": 2,
        "capacity_max": 3,
        "bedrooms": (1, 2),
        "bathrooms": (1, 1),
        "area_sqm": (45, 90),
        "house_types": ["дача", "коттедж", "таунхаус", "дом"],
        "price_inland": (30000, 75000),
        "price_sea": (45000, 120000),
        "title_inland": [
            "Уютный дом для двоих",
            "Компактный коттедж",
            "Дача для пары",
            "Небольшой таунхаус",
        ],
        "title_sea": {
            1: ["Коттедж у моря для двоих", "Студия у пляжа"],
            2: ["Домик во 2-й линии для 2–3 гостей"],
            3: ["Дача у моря для небольшой компании"],
        },
        "extra_amenities": 1,
    },
    "5-6": {
        "label": "5–6 человек",
        "capacity_min": 5,
        "capacity_max": 6,
        "bedrooms": (3, 4),
        "bathrooms": (1, 2),
        "area_sqm": (90, 160),
        "house_types": ["дом", "коттедж", "таунхаус", "вилла"],
        "price_inland": (55000, 130000),
        "price_sea": (70000, 170000),
        "title_inland": [
            "Семейный дом",
            "Коттедж для семьи",
            "Дом для отдыха с друзьями",
            "Загородный дом на 6 гостей",
        ],
        "title_sea": {
            1: ["Семейный дом у пляжа", "Коттедж на первой линии"],
            2: ["Дом во 2-й линии для семьи", "Таунхаус у моря на 6 человек"],
            3: ["Дом в 3-й линии для компании друзей"],
        },
        "extra_amenities": 2,
    },
    "10-12": {
        "label": "10–12 человек",
        "capacity_min": 10,
        "capacity_max": 12,
        "bedrooms": (5, 7),
        "bathrooms": (2, 4),
        "area_sqm": (180, 350),
        "house_types": ["вилла", "дом", "коттедж"],
        "price_inland": (120000, 250000),
        "price_sea": (140000, 320000),
        "title_inland": [
            "Большой дом для компании",
            "Вилла для большой компании",
            "Гостевой дом на 12 человек",
            "Коттедж для корпоративного отдыха",
        ],
        "title_sea": {
            1: ["Вилла на первой линии для компании", "Большой дом у моря"],
            2: ["Гостевой дом во 2-й линии на 10–12 гостей"],
            3: ["Коттедж в 3-й линии для большой компании"],
        },
        "extra_amenities": 3,
    },
}

TITLES_SEA_GENERIC = {
    1: ["Вилла на первой линии", "Дом у пляжа", "Коттедж с выходом к морю"],
    2: ["Дом во второй линии от моря", "Коттедж в 7 минутах от пляжа"],
    3: ["Дом в третьей линии", "Коттедж в 15 минутах от моря"],
}


def amenity_combo(index: int) -> tuple[bool, bool]:
    return [(True, True), (True, False), (False, True), (False, False)][index % 4]


def capacity_key(index: int) -> str:
    return ["2-3", "5-6", "10-12"][index % 3]


def build_amenities(
    has_pool: bool,
    has_sauna: bool,
    rng: random.Random,
    extra_count: int,
) -> list[str]:
    amenities = list(BASE_AMENITIES)
    if has_pool:
        amenities.append("бассейн")
    if has_sauna:
        amenities.append("сауна")
    for extra in rng.sample(EXTRA_AMENITIES, k=extra_count):
        if extra not in amenities:
            amenities.append(extra)
    return amenities


def pick_title(
    *,
    capacity: str,
    near_sea: bool,
    sea_line: int | None,
    index: int,
    rng: random.Random,
) -> str:
    profile = CAPACITY_PROFILES[capacity]
    if near_sea and sea_line is not None:
        titles = profile["title_sea"][sea_line]
    elif near_sea:
        titles = TITLES_SEA_GENERIC[1]
    else:
        titles = profile["title_inland"]
    return f"{rng.choice(titles)} #{index + 1}"


def generate_properties(count: int = 50, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    sea_indices = set(rng.sample(range(count), 18))
    sea_lines = [1, 2, 3] * 6
    rng.shuffle(sea_lines)
    sea_line_iter = iter(sea_lines)

    properties = []
    for i in range(count):
        capacity = capacity_key(i)
        profile = CAPACITY_PROFILES[capacity]
        has_pool, has_sauna = amenity_combo(i)
        amenities = build_amenities(
            has_pool,
            has_sauna,
            rng,
            profile["extra_amenities"],
        )

        bedrooms = rng.randint(*profile["bedrooms"])
        bathrooms = rng.randint(*profile["bathrooms"])
        area = rng.randint(*profile["area_sqm"])
        house_type = rng.choice(profile["house_types"])
        pets_allowed = rng.choice([True, False])
        min_rent_months = rng.choice([1, 1, 2, 3, 6])
        available_from = (date(2026, 6, 1) + timedelta(days=rng.randint(0, 120))).isoformat()

        pool_text = "есть бассейн" if has_pool else "без бассейна"
        sauna_text = "есть сауна" if has_sauna else "без сауны"
        capacity_text = (
            f"Вместимость: {profile['capacity_min']}–{profile['capacity_max']} человек "
            f"({profile['label']})"
        )

        if i in sea_indices:
            region, cities = rng.choice(SEA_REGIONS)
            city = rng.choice(cities)
            location = f"{region}, {city}"
            sea_line = next(sea_line_iter)
            near_sea = True
            title = pick_title(
                capacity=capacity,
                near_sea=True,
                sea_line=sea_line,
                index=i,
                rng=rng,
            )
            price = rng.randint(*profile["price_sea"])

            if sea_line == 1:
                line_desc = "первая линия у моря, до пляжа 1–3 минуты"
            elif sea_line == 2:
                line_desc = "вторая линия от моря, до пляжа 5–10 минут пешком"
            else:
                line_desc = "третья линия от моря, до пляжа 10–20 минут"

            description = (
                f"Приморский объект в {city} ({line_desc}). "
                f"{capacity_text}. "
                f"{pool_text.capitalize()}, {sauna_text}. "
                f"Подходит для аренды от {min_rent_months} мес."
            )
        else:
            location = rng.choice(INLAND)
            near_sea = False
            sea_line = None
            title = pick_title(
                capacity=capacity,
                near_sea=False,
                sea_line=None,
                index=i,
                rng=rng,
            )
            price = rng.randint(*profile["price_inland"])
            place = location.split(", ")[-1]
            description = (
                f"Загородный объект в {place}. "
                f"{capacity_text}. "
                f"{pool_text.capitalize()}, {sauna_text}. "
                f"Подходит для аренды от {min_rent_months} мес."
            )

        properties.append(
            {
                "id": f"house-{i + 1:03d}",
                "title": title,
                "location": location,
                "price_per_month": price,
                "currency": "RUB",
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "area_sqm": area,
                "house_type": house_type,
                "capacity_min": profile["capacity_min"],
                "capacity_max": profile["capacity_max"],
                "capacity_label": profile["label"],
                "amenities": amenities,
                "pets_allowed": pets_allowed,
                "min_rent_months": min_rent_months,
                "available_from": available_from,
                "near_sea": near_sea,
                "sea_line": sea_line,
                "description": description,
            }
        )

    return properties


def main() -> None:
    properties = generate_properties()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(properties, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = Counter(p["sea_line"] for p in properties if p["near_sea"])
    capacity = Counter(p["capacity_label"] for p in properties)
    pool = sum(1 for p in properties if "бассейн" in p["amenities"])
    sauna = sum(1 for p in properties if "сауна" in p["amenities"])

    print(f"Сохранено {len(properties)} объектов в {OUTPUT}")
    print(f"У моря: {sum(1 for p in properties if p['near_sea'])}")
    print(f"Линии: 1={lines[1]}, 2={lines[2]}, 3={lines[3]}")
    print(f"Вместимость: {dict(capacity)}")
    print(f"Бассейн: {pool}, сауна: {sauna}")


if __name__ == "__main__":
    main()
