"""Resolve prefecture names to Jalan SML area codes via bundled area.xml."""

from pathlib import Path

from lxml import etree


DEFAULT_AREA_XML_PATH = Path(__file__).resolve().parent / "data" / "area.xml"


class PrefectureNotFoundError(ValueError):
    """Raised when the requested prefecture does not exist in area.xml."""


def resolve_sml_codes_for_prefecture(
    prefecture_name: str,
    area_xml_path: Path | None = None,
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

    for small_area in prefecture_element.findall(".//SmallArea"):
        code = (small_area.get("cd") or "").strip()
        if not code or len(code) != 6 or not code.isdigit():
            continue

        sml_code = f"SML_{code}"
        if sml_code in seen_codes:
            continue

        seen_codes.add(sml_code)
        sml_codes.append(sml_code)

    if not sml_codes:
        raise ValueError(f"no SML areas found for prefecture: {normalized_prefecture}")

    return sml_codes
