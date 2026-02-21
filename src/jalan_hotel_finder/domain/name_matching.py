"""Domain utilities for loading hotel names and local name matching."""

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def load_hotel_names(names_file: Path) -> list[str]:
    """Load one hotel name per line from a UTF-8 text file."""
    loaded_names: list[str] = []
    seen: set[str] = set()

    with names_file.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            name = raw_line.strip()
            if not name or name in seen:
                continue
            loaded_names.append(name)
            seen.add(name)

    return loaded_names


def filter_hotels_by_names(
    records: Iterable[Mapping[str, Any]],
    target_names: Iterable[str],
) -> list[dict[str, Any]]:
    """Keep hotels where at least one target name is a partial match."""
    normalized_targets = [name for name in target_names if name]

    filtered: list[dict[str, Any]] = []
    for record in records:
        hotel_name = record.get("hotel_name")
        if not isinstance(hotel_name, str):
            continue

        for target_name in normalized_targets:
            if target_name in hotel_name:
                output = dict(record)
                output["matched_name"] = target_name
                filtered.append(output)
                break

    return filtered
