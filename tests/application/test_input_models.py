from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jalan_hotel_finder.application.input_models import (
    MealType,
    SearchAreaInput,
    SearchNamesInput,
)


def test_accepts_valid_search_area_input() -> None:
    actual = SearchAreaInput(
        checkin="2026-03-10",
        pref=["北海道"],
        adults=2,
        nights=2,
        max_price=20000,
        care_kakenagashi=True,
        care_bath_rent=False,
        care_private_openair=False,
        parallel=2,
    )

    assert actual.checkin.isoformat() == "2026-03-10"
    assert actual.parallel == 2
    assert actual.meal_type is None
    assert actual.max_price == 20000


def test_rejects_parallel_over_limit_for_search_area() -> None:
    with pytest.raises(ValidationError):
        SearchAreaInput(
            checkin="2026-03-10",
            pref=["北海道"],
            parallel=11,
        )


def test_accepts_valid_search_names_input() -> None:
    actual = SearchNamesInput(
        names_file=Path("fixtures/names.txt"),
        checkin="2026-03-10",
        pref=["北海道"],
        adults=1,
        nights=1,
        meal_type=MealType.BREAKFAST,
        parallel=1,
    )

    assert actual.checkin.isoformat() == "2026-03-10"
    assert actual.pref == ["北海道"]


def test_search_names_input_defaults_meal_type_to_unspecified() -> None:
    actual = SearchNamesInput(
        names_file=Path("fixtures/names.txt"),
        checkin="2026-03-10",
        pref=["北海道"],
    )

    assert actual.meal_type is None
    assert actual.max_price is None


def test_rejects_negative_max_price_for_search_area() -> None:
    with pytest.raises(ValidationError):
        SearchAreaInput(
            checkin="2026-03-10",
            pref=["北海道"],
            max_price=-1,
        )


def test_rejects_negative_max_price_for_search_names() -> None:
    with pytest.raises(ValidationError):
        SearchNamesInput(
            names_file=Path("fixtures/names.txt"),
            checkin="2026-03-10",
            pref=["北海道"],
            max_price=-1,
        )


def test_rejects_search_names_input_without_pref() -> None:
    with pytest.raises(ValidationError):
        SearchNamesInput(
            names_file=Path("fixtures/names.txt"),
            checkin="2026-03-10",
            pref=[],
        )


def test_rejects_search_names_input_without_names_file() -> None:
    with pytest.raises(ValidationError):
        SearchNamesInput(
            checkin="2026-03-10",
            pref=["北海道"],
        )


def test_rejects_invalid_checkin_format() -> None:
    with pytest.raises(ValidationError):
        SearchAreaInput(
            checkin="2026/03/10",
            pref=["北海道"],
        )
