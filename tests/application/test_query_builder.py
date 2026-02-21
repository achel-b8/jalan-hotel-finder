from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jalan_hotel_finder.application.input_models import MealType, SearchAreaInput
from jalan_hotel_finder.application.query_builder import build_search_area_url


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
