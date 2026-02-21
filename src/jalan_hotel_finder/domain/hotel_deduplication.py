"""Domain logic for hotel URL normalization and deduplication."""

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlsplit


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
) -> list[dict[str, Any]]:
    """Deduplicate hotel records by normalized URL and keep first wins."""
    deduplicated: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for record in records:
        hotel_url = record.get("hotel_url")
        if not isinstance(hotel_url, str) or not hotel_url:
            raise ValueError("record must contain non-empty hotel_url")

        normalized = normalize_hotel_url(hotel_url)
        if normalized in seen_keys:
            continue

        output_record = dict(record)
        output_record["hotel_url_normalized"] = normalized
        deduplicated.append(output_record)
        seen_keys.add(normalized)

    return deduplicated
