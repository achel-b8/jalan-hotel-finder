from pathlib import Path

import pytest

from jalan_hotel_finder.infrastructure.area_xml_resolver import (
    PrefectureAreaNotFoundError,
    PrefectureNotFoundError,
    list_prefecture_names,
    resolve_lrg_codes_for_prefecture,
    resolve_sml_codes_for_prefecture,
)


def test_resolves_sml_codes_for_representative_prefecture() -> None:
    actual = resolve_sml_codes_for_prefecture("北海道")

    assert "SML_010202" in actual
    assert "SML_010302" in actual
    assert len(actual) > 10


def test_excludes_fixed_blocked_sml_codes_from_results() -> None:
    hokkaido = resolve_sml_codes_for_prefecture("北海道")
    ibaraki = resolve_sml_codes_for_prefecture("茨城県")

    assert "SML_013508" not in hokkaido
    assert "SML_101402" not in ibaraki
    assert "SML_101405" in ibaraki


def test_raises_when_prefecture_is_unknown() -> None:
    with pytest.raises(PrefectureNotFoundError):
        resolve_sml_codes_for_prefecture("存在しない都道府県")


def test_returns_non_empty_unique_sml_codes_only() -> None:
    fixture = Path("tests/fixtures/xml/area_with_duplicates.xml")

    actual = resolve_sml_codes_for_prefecture("テスト県", area_xml_path=fixture)

    assert actual == ["SML_990101", "SML_990102"]


def test_resolves_lrg_codes_for_representative_prefecture() -> None:
    actual = resolve_lrg_codes_for_prefecture("北海道")

    assert "LRG_010200" in actual
    assert len(actual) > 5


def test_returns_non_empty_unique_lrg_codes_only() -> None:
    fixture = Path("tests/fixtures/xml/area_with_duplicates.xml")

    actual = resolve_lrg_codes_for_prefecture("テスト県", area_xml_path=fixture)

    assert actual == ["LRG_990100"]


def test_list_prefecture_names_returns_non_empty_unique_names() -> None:
    actual = list_prefecture_names()

    assert "北海道" in actual
    assert len(actual) > 40
    assert len(actual) == len(set(actual))


def test_raises_when_no_sml_area_exists_for_prefecture(tmp_path) -> None:
    fixture = tmp_path / "area_no_sml.xml"
    fixture.write_text(
        "<root><Prefecture name='空県'><LargeArea cd='990100'/></Prefecture></root>",
        encoding="utf-8",
    )

    with pytest.raises(PrefectureAreaNotFoundError):
        resolve_sml_codes_for_prefecture("空県", area_xml_path=fixture)


def test_raises_when_no_lrg_area_exists_for_prefecture(tmp_path) -> None:
    fixture = tmp_path / "area_no_lrg.xml"
    fixture.write_text(
        "<root><Prefecture name='空県'><SmallArea cd='990101'/></Prefecture></root>",
        encoding="utf-8",
    )

    with pytest.raises(PrefectureAreaNotFoundError):
        resolve_lrg_codes_for_prefecture("空県", area_xml_path=fixture)
