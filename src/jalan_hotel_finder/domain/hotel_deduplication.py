"""Domain logic for hotel URL normalization and deduplication."""

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlsplit

# 現行のじゃらん検索結果DOMでは1宿あたり最大3件までしか抽出できない。
# 4件以上を扱うには、宿詳細/プラン一覧ページまで辿る抽出ロジック拡張が必要。
DEFAULT_MAX_RECORDS_PER_HOTEL = 3


def normalize_hotel_url(hotel_url: str) -> str:
    """Build the deduplication key from hotel_url.

    Query strings are ignored and trailing slashes are removed so URLs are
    compared at the path level.
    """
    if not hotel_url:
        raise ValueError("hotel_url must not be empty")

    parsed = urlsplit(hotel_url)
    normalized_path = parsed.path.rstrip("/") or "/"
    return normalized_path


def deduplicate_hotels_by_normalized_url(
    records: Iterable[Mapping[str, Any]],
    *,
    max_records_per_hotel: int = DEFAULT_MAX_RECORDS_PER_HOTEL,
) -> list[dict[str, Any]]:
    """Normalize URLs and keep records up to the per-hotel upper bound."""
    deduplicated: list[dict[str, Any]] = []
    record_counts_by_hotel: dict[str, int] = {}
    per_hotel_limit = max(max_records_per_hotel, 0)

    for record in records:
        hotel_url = record.get("hotel_url")
        if not isinstance(hotel_url, str) or not hotel_url:
            raise ValueError("record must contain non-empty hotel_url")

        normalized = normalize_hotel_url(hotel_url)
        current_count = record_counts_by_hotel.get(normalized, 0)
        if current_count >= per_hotel_limit:
            continue

        output_record = dict(record)
        output_record["hotel_url_normalized"] = normalized
        deduplicated.append(output_record)
        record_counts_by_hotel[normalized] = current_count + 1

    return deduplicated
