"""Area route models shared across resolver, query builder, and services."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AreaRoute:
    """One Jalan route tuple for area search."""

    pref_code: str
    lrg_code: str
    sml_code: str
    pref_name: str
    lrg_name: str
    sml_name: str
