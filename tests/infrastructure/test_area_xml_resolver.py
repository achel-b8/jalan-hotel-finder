from pathlib import Path

import pytest

from jalan_hotel_finder.infrastructure.area_xml_resolver import (
    PrefectureAreaNotFoundError,
    PrefectureNotFoundError,
    list_prefecture_names,
    resolve_area_routes_for_prefecture,
    resolve_lrg_codes_for_prefecture,
    resolve_sml_codes_for_prefecture,
)


def test_resolves_sml_codes_for_representative_prefecture() -> None:
    actual = resolve_sml_codes_for_prefecture("北海道")

    assert "SML_010202" in actual
    assert "SML_010302" in actual
    assert len(actual) > 10


def test_resolves_area_routes_for_representative_prefecture() -> None:
    routes = resolve_area_routes_for_prefecture("北海道")

    assert any(route.sml_code == "SML_010202" for route in routes)
    assert len(routes) > 10


def test_applies_relocated_route_overrides_instead_of_excluding_codes() -> None:
    hokkaido_routes = resolve_area_routes_for_prefecture("北海道")
    ibaraki_routes = resolve_area_routes_for_prefecture("茨城県")
    shizuoka_routes = resolve_area_routes_for_prefecture("静岡県")
    hiroshima_routes = resolve_area_routes_for_prefecture("広島県")

    hokkaido_okushiri = next(route for route in hokkaido_routes if route.sml_code == "SML_013508")
    ibaraki_kashima = next(route for route in ibaraki_routes if route.sml_code == "SML_101402")
    shizuoka_kakegawa = next(route for route in shizuoka_routes if route.sml_code == "SML_212910")
    shizuoka_iwata = next(route for route in shizuoka_routes if route.sml_code == "SML_212912")
    hiroshima_mihara = next(route for route in hiroshima_routes if route.sml_code == "SML_340305")
    hiroshima_kure = next(route for route in hiroshima_routes if route.sml_code == "SML_340308")

    assert hokkaido_okushiri.lrg_code == "LRG_011400"
    assert ibaraki_kashima.lrg_code == "LRG_101100"
    assert shizuoka_kakegawa.lrg_code == "LRG_213700"
    assert shizuoka_iwata.lrg_code == "LRG_213700"
    assert hiroshima_mihara.lrg_code == "LRG_341100"
    assert hiroshima_kure.lrg_code == "LRG_341100"


def test_excludes_remaining_fixed_invalid_sml_codes_from_results() -> None:
    shiga = resolve_sml_codes_for_prefecture("滋賀県")

    assert "SML_251105" not in shiga


def test_previous_excluded_codes_are_now_included_via_relocated_routes() -> None:
    shizuoka = resolve_sml_codes_for_prefecture("静岡県")
    hiroshima = resolve_sml_codes_for_prefecture("広島県")

    assert "SML_212910" in shizuoka
    assert "SML_212912" in shizuoka
    assert "SML_340305" in hiroshima
    assert "SML_340308" in hiroshima


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
