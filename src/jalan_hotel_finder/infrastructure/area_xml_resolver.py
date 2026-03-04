"""Resolve prefecture names to Jalan area route codes via bundled area.xml."""

from collections.abc import Mapping
from pathlib import Path

from lxml import etree

from jalan_hotel_finder.application.area_routes import AreaRoute


DEFAULT_AREA_XML_PATH = Path(__file__).resolve().parent / "data" / "area.xml"
EXCLUDED_SML_CODES_V1: set[str] = {
    # 2026-03-05 live observation: this SML route remains invalid/non-public.
    "SML_251105",
}
RELOCATED_SML_TO_LRG_OVERRIDES_V1: dict[str, str] = {
    # 2026-03-05 live observation: these SML are now valid under different LRG routes.
    "SML_013508": "LRG_011400",
    "SML_101402": "LRG_101100",
    "SML_212910": "LRG_213700",
    "SML_212912": "LRG_213700",
    "SML_340305": "LRG_341100",
    "SML_340308": "LRG_341100",
}


class PrefectureNotFoundError(ValueError):
    """Raised when the requested prefecture does not exist in area.xml."""


class PrefectureAreaNotFoundError(ValueError):
    """Raised when no valid area codes exist for the requested prefecture."""


def list_prefecture_names(area_xml_path: Path | None = None) -> list[str]:
    """Return unique, non-empty prefecture names from area.xml."""
    xml_path = area_xml_path or DEFAULT_AREA_XML_PATH
    root = etree.parse(str(xml_path)).getroot()

    names: list[str] = []
    seen: set[str] = set()

    for prefecture in root.findall("./Prefecture"):
        name = (prefecture.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)

    if not names:
        raise ValueError("no prefecture names found in area.xml")

    return names


def resolve_sml_codes_for_prefecture(
    prefecture_name: str,
    area_xml_path: Path | None = None,
    excluded_sml_codes: set[str] | None = None,
    relocated_sml_to_lrg_overrides: Mapping[str, str] | None = None,
) -> list[str]:
    """Return unique, non-empty SML codes for one prefecture name."""
    routes = resolve_area_routes_for_prefecture(
        prefecture_name=prefecture_name,
        area_xml_path=area_xml_path,
        excluded_sml_codes=excluded_sml_codes,
        relocated_sml_to_lrg_overrides=relocated_sml_to_lrg_overrides,
    )
    return [route.sml_code for route in routes]


def resolve_area_routes_for_prefecture(
    prefecture_name: str,
    area_xml_path: Path | None = None,
    excluded_sml_codes: set[str] | None = None,
    relocated_sml_to_lrg_overrides: Mapping[str, str] | None = None,
) -> list[AreaRoute]:
    """Return unique, non-empty area routes for one prefecture name."""
    normalized_prefecture = prefecture_name.strip()
    if not normalized_prefecture:
        raise ValueError("prefecture_name must not be empty")

    xml_path = area_xml_path or DEFAULT_AREA_XML_PATH
    root = etree.parse(str(xml_path)).getroot()

    prefecture_element = None
    for candidate in root.findall("./Prefecture"):
        if candidate.get("name") == normalized_prefecture:
            prefecture_element = candidate
            break

    if prefecture_element is None:
        raise PrefectureNotFoundError(
            f"prefecture not found in area.xml: {normalized_prefecture}"
        )

    pref_code = (prefecture_element.get("cd") or "").strip()
    if len(pref_code) != 6 or not pref_code.isdigit():
        raise PrefectureAreaNotFoundError(
            f"invalid prefecture code in area.xml: {normalized_prefecture}"
        )

    lrg_name_by_code: dict[str, str] = {}
    for large_area in prefecture_element.findall("./LargeArea"):
        code = (large_area.get("cd") or "").strip()
        if not code or len(code) != 6 or not code.isdigit():
            continue
        lrg_name_by_code[f"LRG_{code}"] = (large_area.get("name") or "").strip()

    routes: list[AreaRoute] = []
    seen_sml_codes: set[str] = set()
    excluded = (
        EXCLUDED_SML_CODES_V1
        if excluded_sml_codes is None
        else excluded_sml_codes
    )
    relocated = (
        RELOCATED_SML_TO_LRG_OVERRIDES_V1
        if relocated_sml_to_lrg_overrides is None
        else relocated_sml_to_lrg_overrides
    )

    for large_area in prefecture_element.findall("./LargeArea"):
        lrg_digits = (large_area.get("cd") or "").strip()
        if not lrg_digits or len(lrg_digits) != 6 or not lrg_digits.isdigit():
            continue

        base_lrg_code = f"LRG_{lrg_digits}"
        base_lrg_name = (large_area.get("name") or "").strip()

        for small_area in large_area.findall("./SmallArea"):
            sml_digits = (small_area.get("cd") or "").strip()
            if not sml_digits or len(sml_digits) != 6 or not sml_digits.isdigit():
                continue

            sml_code = f"SML_{sml_digits}"
            if sml_code in excluded:
                continue
            if sml_code in seen_sml_codes:
                continue

            resolved_lrg_code = relocated.get(sml_code, base_lrg_code)
            resolved_lrg_name = lrg_name_by_code.get(resolved_lrg_code, base_lrg_name)

            routes.append(
                AreaRoute(
                    pref_code=pref_code,
                    lrg_code=resolved_lrg_code,
                    sml_code=sml_code,
                    pref_name=normalized_prefecture,
                    lrg_name=resolved_lrg_name,
                    sml_name=(small_area.get("name") or "").strip(),
                )
            )
            seen_sml_codes.add(sml_code)

    if not routes:
        raise PrefectureAreaNotFoundError(
            f"no SML areas found for prefecture: {normalized_prefecture}"
        )

    return routes


def resolve_lrg_codes_for_prefecture(
    prefecture_name: str,
    area_xml_path: Path | None = None,
) -> list[str]:
    """Return unique, non-empty LRG codes for one prefecture name."""
    normalized_prefecture = prefecture_name.strip()
    if not normalized_prefecture:
        raise ValueError("prefecture_name must not be empty")

    xml_path = area_xml_path or DEFAULT_AREA_XML_PATH
    root = etree.parse(str(xml_path)).getroot()

    prefecture_element = None
    for candidate in root.findall("./Prefecture"):
        if candidate.get("name") == normalized_prefecture:
            prefecture_element = candidate
            break

    if prefecture_element is None:
        raise PrefectureNotFoundError(
            f"prefecture not found in area.xml: {normalized_prefecture}"
        )

    lrg_codes: list[str] = []
    seen_codes: set[str] = set()

    for large_area in prefecture_element.findall(".//LargeArea"):
        code = (large_area.get("cd") or "").strip()
        if not code or len(code) != 6 or not code.isdigit():
            continue

        lrg_code = f"LRG_{code}"
        if lrg_code in seen_codes:
            continue

        seen_codes.add(lrg_code)
        lrg_codes.append(lrg_code)

    if not lrg_codes:
        raise PrefectureAreaNotFoundError(
            f"no LRG areas found for prefecture: {normalized_prefecture}"
        )

    return lrg_codes
