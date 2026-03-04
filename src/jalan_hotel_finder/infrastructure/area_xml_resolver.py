"""Resolve prefecture names to Jalan SML area codes via bundled area.xml."""

from pathlib import Path

from lxml import etree


DEFAULT_AREA_XML_PATH = Path(__file__).resolve().parent / "data" / "area.xml"
EXCLUDED_SML_CODES_V1: set[str] = {
    # 2026-02-24 observation: this area consistently returns Jalan error page.
    "SML_013508",
    # 2026-03-04 observation: this area consistently returns Jalan error page.
    "SML_101402",
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
) -> list[str]:
    """Return unique, non-empty SML codes for one prefecture name."""
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

    sml_codes: list[str] = []
    seen_codes: set[str] = set()
    excluded = excluded_sml_codes or EXCLUDED_SML_CODES_V1

    for small_area in prefecture_element.findall(".//SmallArea"):
        code = (small_area.get("cd") or "").strip()
        if not code or len(code) != 6 or not code.isdigit():
            continue

        sml_code = f"SML_{code}"
        if sml_code in excluded:
            continue
        if sml_code in seen_codes:
            continue

        seen_codes.add(sml_code)
        sml_codes.append(sml_code)

    if not sml_codes:
        raise PrefectureAreaNotFoundError(
            f"no SML areas found for prefecture: {normalized_prefecture}"
        )

    return sml_codes


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
