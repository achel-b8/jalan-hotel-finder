"""Domain utilities for loading hotel names and local name matching."""

import csv
from enum import StrEnum
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from jalan_hotel_finder.domain.hotel_deduplication import normalize_hotel_url


class PreferredOption(StrEnum):
    """Supported preferred-option tokens in candidate CSV."""

    CARE_KAKENAGASHI = "care-kakenagashi"
    CARE_BATH_RENT = "care-bath-rent"
    CARE_PRIVATE_OPENAIR = "care-private-openair"


class InvalidPreferredOptionError(ValueError):
    """Raised when candidate CSV includes an unsupported preferred option."""


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


def load_preferred_options_by_name(names_file: Path) -> dict[str, set[PreferredOption]]:
    """Load preferred options from CSV and group by hotel name."""
    if names_file.suffix.lower() != ".csv":
        return {}

    options_by_name: dict[str, set[PreferredOption]] = {}
    with names_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_index, row in enumerate(reader, start=2):
            hotel_name = _first_non_empty(row, ["宿名", "hotel_name", "name"])
            if hotel_name is None:
                continue

            preferred_options = _parse_preferred_options(
                row,
                names_file=names_file,
                row_index=row_index,
            )
            if not preferred_options:
                continue

            options_by_name.setdefault(hotel_name, set()).update(preferred_options)
    return options_by_name


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


def _parse_preferred_options(
    row: Mapping[str, str | None],
    names_file: Path,
    row_index: int,
) -> set[PreferredOption]:
    raw_options = _first_non_empty(row, ["優先オプション", "preferred_options", "options"])
    if raw_options is None:
        return set()

    parsed: set[PreferredOption] = set()
    for raw_option in raw_options.split("|"):
        option = raw_option.strip()
        if not option:
            continue
        try:
            parsed.add(PreferredOption(option))
        except ValueError as error:
            raise InvalidPreferredOptionError(
                f"unsupported preferred option in {names_file}:{row_index}: {option}"
            ) from error

    return parsed


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
