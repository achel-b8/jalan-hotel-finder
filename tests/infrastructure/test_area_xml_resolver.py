from pathlib import Path

import pytest

from jalan_hotel_finder.infrastructure.area_xml_resolver import (
    PrefectureNotFoundError,
    resolve_sml_codes_for_prefecture,
)


def test_resolves_sml_codes_for_representative_prefecture() -> None:
    actual = resolve_sml_codes_for_prefecture("北海道")

    assert "SML_010202" in actual
    assert "SML_010302" in actual
    assert len(actual) > 10


def test_raises_when_prefecture_is_unknown() -> None:
    with pytest.raises(PrefectureNotFoundError):
        resolve_sml_codes_for_prefecture("存在しない都道府県")


def test_returns_non_empty_unique_sml_codes_only() -> None:
    fixture = Path("tests/fixtures/xml/area_with_duplicates.xml")

    actual = resolve_sml_codes_for_prefecture("テスト県", area_xml_path=fixture)

    assert actual == ["SML_990101", "SML_990102"]
