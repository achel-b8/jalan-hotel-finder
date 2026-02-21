from pathlib import Path

from jalan_hotel_finder.domain.name_matching import (
    filter_hotels_by_names,
    load_hotel_names,
)


def test_load_hotel_names_reads_one_name_per_line(tmp_path: Path) -> None:
    file_path = tmp_path / "names.txt"
    file_path.write_text("\n札幌温泉ホテル\n函館シティホテル\n", encoding="utf-8")

    actual = load_hotel_names(file_path)

    assert actual == ["札幌温泉ホテル", "函館シティホテル"]


def test_filter_hotels_by_names_partial_match_and_non_match() -> None:
    records = [
        {"hotel_name": "札幌温泉ホテル", "hotel_url": "https://www.jalan.net/yad1/"},
        {"hotel_name": "小樽ベイホテル", "hotel_url": "https://www.jalan.net/yad2/"},
    ]

    actual = filter_hotels_by_names(records, ["札幌", "函館"])

    assert len(actual) == 1
    assert actual[0]["hotel_name"] == "札幌温泉ホテル"
    assert actual[0]["matched_name"] == "札幌"


def test_filter_hotels_by_names_returns_empty_when_no_match() -> None:
    records = [{"hotel_name": "小樽ベイホテル", "hotel_url": "https://www.jalan.net/yad2/"}]

    assert filter_hotels_by_names(records, ["札幌", "函館"]) == []
