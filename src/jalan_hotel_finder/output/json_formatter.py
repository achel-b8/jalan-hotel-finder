"""Human-readable formatting for CLI output records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlsplit

DEFAULT_MAX_PLANS_PER_HOTEL = 5


def format_search_results(
    records: Iterable[Mapping[str, Any]],
    *,
    max_plans_per_hotel: int = DEFAULT_MAX_PLANS_PER_HOTEL,
) -> str:
    """Format records into a human-readable list."""
    hotel_rows: list[dict[str, Any]] = []
    grouped_hotels: dict[str, dict[str, Any]] = {}

    for index, record in enumerate(records):
        output = dict(record)
        group_key = _build_group_key(output, fallback_index=index)
        group = grouped_hotels.get(group_key)
        if group is None:
            group = {
                "hotel_name": _as_text(output.get("hotel_name"), fallback="宿名未取得"),
                "hotel_url": _as_text(output.get("hotel_url"), fallback="URL未取得"),
                "plans": [],
            }
            grouped_hotels[group_key] = group
            hotel_rows.append(group)

        plans: list[dict[str, Any]] = group["plans"]
        if len(plans) >= max(max_plans_per_hotel, 0):
            continue

        plans.append(
            {
                "plan_name": _as_text(output.get("plan_name"), fallback="プラン名未取得"),
                "price": output.get("price"),
            }
        )

    if not hotel_rows:
        return "該当する宿はありませんでした。"

    lines: list[str] = [f"検索結果: {len(hotel_rows)}件", ""]
    for index, hotel in enumerate(hotel_rows, start=1):
        lines.append(f"[{index}] 宿名: {hotel['hotel_name']}")
        lines.append(f"URL: {hotel['hotel_url']}")
        plans = hotel["plans"] or [{"plan_name": "プラン名未取得", "price": None}]
        for plan_index, plan in enumerate(plans, start=1):
            lines.append(
                f"  - プラン{plan_index}: {plan['plan_name']} / {_format_price(plan['price'])}"
            )
        if index < len(hotel_rows):
            lines.append("")

    return "\n".join(lines)


def serialize_search_results(records: Iterable[Mapping[str, Any]]) -> str:
    """Backward compatible alias kept for existing call sites."""
    return format_search_results(
        records,
        max_plans_per_hotel=DEFAULT_MAX_PLANS_PER_HOTEL,
    )


def _build_group_key(record: Mapping[str, Any], fallback_index: int) -> str:
    normalized_url = record.get("hotel_url_normalized")
    if isinstance(normalized_url, str) and normalized_url.strip():
        return normalized_url.strip().rstrip("/") or "/"

    hotel_url = record.get("hotel_url")
    if isinstance(hotel_url, str) and hotel_url.strip():
        parsed = urlsplit(hotel_url)
        normalized_path = parsed.path.rstrip("/")
        if normalized_path:
            return normalized_path
        return hotel_url.strip()

    return f"unknown-{fallback_index}"


def _as_text(value: Any, *, fallback: str) -> str:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return fallback


def _format_price(value: Any) -> str:
    if isinstance(value, bool):
        return "価格未取得"
    if isinstance(value, (int, float)):
        return f"{int(value):,}円"
    return "価格未取得"
