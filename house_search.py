"""Подбор домов по критериям пользователя."""
from __future__ import annotations

import html
from typing import Any

from personality import BOT_NAME

MAX_RESULTS = 8

REGION_ANY = "any"
REGION_SEA = "sea"
REGION_MOSCOW = "moscow"
REGION_KRASNODAR = "krasnodar"
REGION_CRIMEA = "crimea"

GUESTS_ANY = "any"
GUESTS_2_3 = "2-3"
GUESTS_4_6 = "4-6"
GUESTS_7_10 = "7-10"
GUESTS_11_PLUS = "11+"

BUDGET_ANY = "any"
BUDGET_50 = "50000"
BUDGET_100 = "100000"
BUDGET_150 = "150000"
BUDGET_200 = "200000"

REGION_LABELS = {
    REGION_ANY: "любой регион",
    REGION_SEA: "у моря",
    REGION_MOSCOW: "Подмосковье",
    REGION_KRASNODAR: "Краснодарский край",
    REGION_CRIMEA: "Крым",
}

GUESTS_LABELS = {
    GUESTS_ANY: "любое число гостей",
    GUESTS_2_3: "2–3 человека",
    GUESTS_4_6: "4–6 человек",
    GUESTS_7_10: "7–10 человек",
    GUESTS_11_PLUS: "11 и больше",
}

BUDGET_LABELS = {
    BUDGET_ANY: "без ограничения",
    BUDGET_50: "до 50 000 ₽",
    BUDGET_100: "до 100 000 ₽",
    BUDGET_150: "до 150 000 ₽",
    BUDGET_200: "до 200 000 ₽",
}


def _matches_region(item: dict[str, Any], region: str) -> bool:
    if region == REGION_ANY:
        return True
    location = item.get("location", "")
    if region == REGION_SEA:
        return bool(item.get("near_sea"))
    if region == REGION_MOSCOW:
        return "Московская область" in location
    if region == REGION_KRASNODAR:
        return "Краснодарский край" in location
    if region == REGION_CRIMEA:
        return "Крым" in location
    return True


def _guests_bounds(guests: str) -> tuple[int | None, int | None]:
    mapping = {
        GUESTS_2_3: (2, 3),
        GUESTS_4_6: (4, 6),
        GUESTS_7_10: (7, 10),
        GUESTS_11_PLUS: (11, None),
    }
    return mapping.get(guests, (None, None))


def _matches_guests(item: dict[str, Any], guests: str) -> bool:
    if guests == GUESTS_ANY:
        return True
    need_min, need_max = _guests_bounds(guests)
    cap_min = int(item.get("capacity_min", 0))
    cap_max = int(item.get("capacity_max", cap_min))
    if need_min is None:
        return True
    if cap_max < need_min:
        return False
    if need_max is not None and cap_min > need_max:
        return False
    return True


def _budget_limit(budget: str) -> int | None:
    if budget == BUDGET_ANY:
        return None
    try:
        return int(budget)
    except ValueError:
        return None


def _matches_budget(item: dict[str, Any], budget: str) -> bool:
    limit = _budget_limit(budget)
    if limit is None:
        return True
    return int(item.get("price_per_month", 0)) <= limit


def _score_item(item: dict[str, Any], guests: str, budget: str) -> float:
    score = 0.0
    price = int(item.get("price_per_month", 0))
    limit = _budget_limit(budget)
    if limit is not None:
        score += max(0, limit - price) / max(limit, 1) * 40
    else:
        score += 10

    need_min, need_max = _guests_bounds(guests)
    if need_min is not None:
        cap_min = int(item.get("capacity_min", 0))
        cap_max = int(item.get("capacity_max", cap_min))
        if need_max is not None:
            ideal = (need_min + need_max) / 2
            mid = (cap_min + cap_max) / 2
            score += max(0, 20 - abs(mid - ideal) * 2)
        else:
            score += min(20, cap_max - need_min)

    if item.get("near_sea"):
        score += 5
    return score


def filter_properties(
    properties: list[dict[str, Any]],
    *,
    region: str,
    guests: str,
    budget: str,
) -> list[dict[str, Any]]:
    matched = [
        item
        for item in properties
        if _matches_region(item, region)
        and _matches_guests(item, guests)
        and _matches_budget(item, budget)
    ]
    matched.sort(
        key=lambda item: _score_item(item, guests, budget),
        reverse=True,
    )
    return matched


def format_property_card(item: dict[str, Any], index: int) -> str:
    sea = ""
    if item.get("near_sea"):
        line = item.get("sea_line")
        sea = f", у моря ({line}-я линия)" if line else ", у моря"
    location = html.escape(item.get("location", "").split(",")[-1].strip())
    title = html.escape(str(item.get("title", "")))
    price = f"{int(item['price_per_month']):,}".replace(",", " ")
    return (
        f"{index}. <b>{html.escape(item['id'])}</b> — {title}\n"
        f"   📍 {location}{sea}\n"
        f"   👥 {html.escape(str(item.get('capacity_label', '?')))} · "
        f"💰 {price} ₽/мес"
    )


def format_search_results(
    items: list[dict[str, Any]],
    *,
    region: str,
    guests: str,
    budget: str,
    total_count: int,
) -> str:
    region_label = REGION_LABELS.get(region, region)
    guests_label = GUESTS_LABELS.get(guests, guests)
    budget_label = BUDGET_LABELS.get(budget, budget)

    if not items:
        return (
            f"Mamma mia! По запросу ({region_label}, {guests_label}, {budget_label}) "
            f"ничего не нашлось 😅\n\n"
            "Попробуйте /houses с другими параметрами — например, «без ограничения» по бюджету "
            "или «любой регион»."
        )

    shown = items[:MAX_RESULTS]
    header = (
        f"🏡 <b>Подбор от {html.escape(BOT_NAME)}</b> — нашлось {len(items)} из {total_count} домов\n"
        f"Критерии: {html.escape(region_label)} · {html.escape(guests_label)} · "
        f"{html.escape(budget_label)}\n"
    )
    if len(items) > MAX_RESULTS:
        header += f"Показываю топ-{MAX_RESULTS}, alla grande:\n\n"
    else:
        header += "\n"

    cards = "\n\n".join(format_property_card(item, i) for i, item in enumerate(shown, 1))
    footer = (
        "\n\n👇 Нажмите код дома на кнопке — покажу подробности.\n"
        "Или «📞 Заказать обратный звонок» — перезвоним и поможем с выбором."
    )
    return header + cards + footer
