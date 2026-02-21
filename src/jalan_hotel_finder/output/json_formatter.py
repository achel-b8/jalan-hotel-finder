"""JSON serialization for CLI output records."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any


def serialize_search_results(records: Iterable[Mapping[str, Any]]) -> str:
    """Serialize records to JSON and normalize search-type specific fields."""
    normalized_records: list[dict[str, Any]] = []

    for record in records:
        output = dict(record)
        search_type = output.get("search_type")

        if search_type == "area":
            output.pop("matched_name", None)
        elif search_type == "name":
            output.setdefault("matched_name", "")

        normalized_records.append(output)

    return json.dumps(normalized_records, ensure_ascii=False)
