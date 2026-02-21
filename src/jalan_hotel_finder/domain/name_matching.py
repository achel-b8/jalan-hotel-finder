"""Domain utilities for loading hotel names and local name matching."""

import csv
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from jalan_hotel_finder.domain.hotel_deduplication import normalize_hotel_url


def load_hotel_names(names_file: Path) -> list[str]:
    """Load name/url candidates from UTF-8 txt or csv."""
    if names_file.suffix.lower() == ".csv":
        return _load_hotel_names_from_csv(names_file)
    return _load_hotel_names_from_text(names_file)


def _load_hotel_names_from_text(names_file: Path) -> list[str]:
    loaded_names: list[str] = []
    seen: set[str] = set()

    with names_file.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            _append_unique_candidate(loaded_names, seen, raw_line.strip())

    return loaded_names


def _load_hotel_names_from_csv(names_file: Path) -> list[str]:
    loaded_names: list[str] = []
    seen: set[str] = set()

    with names_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            hotel_name = _first_non_empty(row, ["宿名", "hotel_name", "name"])
            hotel_url = _first_non_empty(row, ["URL", "url", "hotel_url"])
            _append_unique_candidate(loaded_names, seen, hotel_name)
            _append_unique_candidate(loaded_names, seen, hotel_url)

    return loaded_names


def filter_hotels_by_names(
    records: Iterable[Mapping[str, Any]],
    target_names: Iterable[str],
) -> list[dict[str, Any]]:
    """Keep hotels where one target name/url matches."""
    name_targets: list[str] = []
    url_targets_by_normalized: dict[str, str] = {}

    for target in target_names:
        if not isinstance(target, str):
            continue
        stripped = target.strip()
        if not stripped:
            continue

        normalized_target_url = _normalize_target_hotel_url(stripped)
        if normalized_target_url is not None:
            url_targets_by_normalized.setdefault(normalized_target_url, stripped)
            continue

        name_targets.append(stripped)

    filtered: list[dict[str, Any]] = []
    for record in records:
        matched_target = _find_matched_target(record, name_targets, url_targets_by_normalized)
        if matched_target is None:
            continue
        output = dict(record)
        output["matched_name"] = matched_target
        filtered.append(output)

    return filtered


def _append_unique_candidate(loaded_names: list[str], seen: set[str], raw_value: str | None) -> None:
    if raw_value is None:
        return
    value = raw_value.strip()
    if not value or value in seen:
        return
    loaded_names.append(value)
    seen.add(value)


def _first_non_empty(row: Mapping[str, str | None], keys: list[str]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and value.strip():
            return value.strip()
    return None


def _normalize_target_hotel_url(target: str) -> str | None:
    maybe_path = re.search(r"/yad\d+", target)
    if maybe_path is None:
        return None
    return maybe_path.group(0)


def _find_matched_target(
    record: Mapping[str, Any],
    name_targets: list[str],
    url_targets_by_normalized: Mapping[str, str],
) -> str | None:
    hotel_name = record.get("hotel_name")
    if isinstance(hotel_name, str):
        for target_name in name_targets:
            if target_name in hotel_name:
                return target_name

    hotel_url = record.get("hotel_url")
    if isinstance(hotel_url, str) and hotel_url:
        normalized_url = normalize_hotel_url(hotel_url)
        return url_targets_by_normalized.get(normalized_url)

    return None
