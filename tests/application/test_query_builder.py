from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jalan_hotel_finder.application.input_models import (
    KeywordEncoding,
    MealType,
    SearchAreaInput,
)
from jalan_hotel_finder.application.query_builder import (
    build_keyword_search_url,
    build_search_area_url,
)


def _parse_params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


def test_build_search_area_url_maps_checkin_to_stay_date_params() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10")

    url = build_search_area_url("SML_010202", user_input)

    parsed = urlparse(url)
    params = _parse_params(url)

    assert parsed.scheme == "https"
    assert parsed.netloc == "www.jalan.net"
    assert parsed.path == "/010000/LRG_010200/SML_010202/"
    assert params["stayYear"] == ["2026"]
    assert params["stayMonth"] == ["03"]
    assert params["stayDay"] == ["10"]


@pytest.mark.parametrize(
    ("meal_type", "expected"),
    [
        (MealType.NONE, "0"),
        (MealType.BREAKFAST, "1"),
        (MealType.DINNER, "2"),
        (MealType.TWO_MEALS, "3"),
    ],
)
def test_build_search_area_url_maps_meal_type_enum_values(
    meal_type: MealType,
    expected: str,
) -> None:
    user_input = SearchAreaInput(checkin="2026-03-10", meal_type=meal_type)

    url = build_search_area_url("SML_010202", user_input)
    params = _parse_params(url)

    assert params["mealType"] == [expected]


def test_build_search_area_url_sets_fixed_query_params() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10")

    url = build_search_area_url("SML_010202", user_input)
    params = _parse_params(url)

    assert params["roomCount"] == ["1"]
    assert params["dateUndecided"] == ["0"]
    assert params["careBath"] == ["0"]


def test_build_search_area_url_includes_max_price_when_max_price_is_specified() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10", max_price=15000)

    url = build_search_area_url("SML_010202", user_input)
    params = _parse_params(url)

    assert params["maxPrice"] == ["15000"]


def test_build_search_area_url_omits_max_price_when_max_price_is_unspecified() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10")

    url = build_search_area_url("SML_010202", user_input)
    params = _parse_params(url)

    assert "maxPrice" not in params


def test_build_search_area_url_omits_meal_type_when_unspecified() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10")

    url = build_search_area_url("SML_010202", user_input)
    params = _parse_params(url)

    assert "mealType" not in params


def test_build_search_area_url_includes_care_params_when_enabled() -> None:
    user_input = SearchAreaInput(
        checkin="2026-03-10",
        care_kakenagashi=True,
        care_bath_rent=True,
        care_private_openair=True,
    )

    url = build_search_area_url("SML_010202", user_input)
    params = _parse_params(url)

    assert params["careKake"] == ["1"]
    assert params["careBathRent"] == ["1"]
    assert params["carePribateBath"] == ["1"]


def test_build_search_area_url_omits_optional_care_params_when_disabled() -> None:
    user_input = SearchAreaInput(
        checkin="2026-03-10",
        care_kakenagashi=False,
        care_bath_rent=False,
        care_private_openair=False,
    )

    url = build_search_area_url("SML_010202", user_input)
    params = _parse_params(url)

    assert "careKake" not in params
    assert "careBathRent" not in params
    assert "carePribateBath" not in params


def test_build_keyword_search_url_uses_cp932_percent_encoding() -> None:
    url = build_keyword_search_url("ピリカレラ", KeywordEncoding.CP932)

    parsed = urlparse(url)
    assert parsed.path == "/uw/uwp2011/uww2011init.do"
    assert "keyword=%83s%83%8A%83J%83%8C%83%89" in parsed.query
    params = _parse_params(url)
    assert params["distCd"] == ["06"]
    assert params["rootCd"] == ["7701"]
    assert params["screenId"] == ["FWPCTOP"]
    assert params["ccnt"] == ["button-fw"]


def test_build_keyword_search_url_treats_auto_as_cp932() -> None:
    cp932_url = build_keyword_search_url("川島旅館", KeywordEncoding.CP932)
    auto_url = build_keyword_search_url("川島旅館", KeywordEncoding.AUTO)

    assert cp932_url == auto_url


def test_build_keyword_search_url_includes_max_price_when_max_price_is_specified() -> None:
    url = build_keyword_search_url("ピリカレラ", KeywordEncoding.CP932, max_price=5000)
    params = _parse_params(url)

    assert params["maxPrice"] == ["5000"]


def test_build_keyword_search_url_omits_max_price_when_max_price_is_unspecified() -> None:
    url = build_keyword_search_url("ピリカレラ", KeywordEncoding.CP932)
    params = _parse_params(url)

    assert "maxPrice" not in params
