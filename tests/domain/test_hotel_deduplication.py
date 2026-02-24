from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jalan_hotel_finder.domain.hotel_deduplication import (
    deduplicate_hotels_by_normalized_url,
    normalize_hotel_url,
)


def test_hotel_url_normalized_removes_query_and_trailing_slash() -> None:
    assert (
        normalize_hotel_url("https://www.jalan.net/yad123456/?plan=abc&idx=30")
        == "/yad123456"
    )


def test_deduplication_keeps_records_when_query_is_different_within_limit() -> None:
    records = [
        {
            "hotel_name": "A",
            "hotel_url": "https://www.jalan.net/yad111111/?plan=first",
            "plan_name": "first plan",
            "price": 10000,
        },
        {
            "hotel_name": "A",
            "hotel_url": "https://www.jalan.net/yad111111/?plan=second",
            "plan_name": "second plan",
            "price": 11000,
        },
    ]

    actual = deduplicate_hotels_by_normalized_url(records)

    assert len(actual) == 2
    assert actual[0]["hotel_url_normalized"] == "/yad111111"
    assert actual[1]["hotel_url_normalized"] == "/yad111111"


def test_deduplication_normalizes_trailing_slash_and_keeps_records_within_limit() -> None:
    records = [
        {
            "hotel_name": "A",
            "hotel_url": "https://www.jalan.net/yad222222/",
            "plan_name": "first plan",
            "price": 10000,
        },
        {
            "hotel_name": "A",
            "hotel_url": "https://www.jalan.net/yad222222",
            "plan_name": "second plan",
            "price": 9000,
        },
    ]

    actual = deduplicate_hotels_by_normalized_url(records)

    assert len(actual) == 2
    assert actual[0]["hotel_url_normalized"] == "/yad222222"
    assert actual[1]["hotel_url_normalized"] == "/yad222222"


def test_deduplication_limits_to_three_records_per_hotel_by_default() -> None:
    records = [
        {
            "hotel_name": "A",
            "hotel_url": f"https://www.jalan.net/yad333333/?plan={index}",
            "plan_name": f"plan {index}",
            "price": 10000 + index,
        }
        for index in range(1, 5)
    ]

    actual = deduplicate_hotels_by_normalized_url(records)

    assert len(actual) == 3
    assert [record["plan_name"] for record in actual] == [
        "plan 1",
        "plan 2",
        "plan 3",
    ]
