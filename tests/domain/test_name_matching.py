from pathlib import Path

import pytest

from jalan_hotel_finder.domain.name_matching import (
    InvalidPreferredOptionError,
    PreferredOption,
    filter_hotels_by_names,
    load_hotel_names,
    load_preferred_options_by_name,
)


def test_load_hotel_names_reads_one_name_per_line(tmp_path: Path) -> None:
    file_path = tmp_path / "names.txt"
    file_path.write_text("\n札幌温泉ホテル\n函館シティホテル\n", encoding="utf-8")

    actual = load_hotel_names(file_path)

    assert actual == ["札幌温泉ホテル", "函館シティホテル"]


def test_load_hotel_names_reads_csv_name_url_and_options_columns(tmp_path: Path) -> None:
    file_path = tmp_path / "candidates.csv"
    file_path.write_text(
        "宿名,URL,優先オプション\n"
        "川島旅館,https://www.jalan.net/yad386526/?yadNo=386526,care-kakenagashi|care-bath-rent\n"
        "ピリカ,https://www.jalan.net/yad377160/?yadNo=377160,\n",
        encoding="utf-8",
    )

    actual = load_hotel_names(file_path)

    assert actual == [
        "川島旅館",
        "https://www.jalan.net/yad386526/?yadNo=386526",
        "ピリカ",
        "https://www.jalan.net/yad377160/?yadNo=377160",
    ]


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


def test_filter_hotels_by_names_matches_when_candidate_is_hotel_url() -> None:
    target_urls = [
        "https://www.jalan.net/yad386526/?yadNo=386526&convertedFlg=1&ccnt=link-yad-386526-%E5%B7%9D%E5%B3%B6%E6%97%85%E9%A4%A8-0",
        "https://www.jalan.net/yad377160/?yadNo=377160&convertedFlg=1&ccnt=link-yad-377160-%E3%83%94%E3%83%AA%E3%82%AB-0",
    ]
    records = [
        {"hotel_name": "川島旅館", "hotel_url": "https://www.jalan.net/yad386526/?plan=first"},
        {"hotel_name": "ピリカ", "hotel_url": "https://www.jalan.net/yad377160/?plan=second"},
        {"hotel_name": "小樽ベイホテル", "hotel_url": "https://www.jalan.net/yad2/"},
    ]

    actual = filter_hotels_by_names(records, target_urls)

    assert len(actual) == 2
    assert actual[0]["hotel_name"] == "川島旅館"
    assert actual[0]["matched_name"] == target_urls[0]
    assert actual[1]["hotel_name"] == "ピリカ"
    assert actual[1]["matched_name"] == target_urls[1]


def test_load_preferred_options_by_name_reads_supported_tokens(tmp_path: Path) -> None:
    file_path = tmp_path / "candidates.csv"
    file_path.write_text(
        "宿名,URL,優先オプション\n"
        "川島旅館,https://www.jalan.net/yad386526/,care-kakenagashi|care-bath-rent\n"
        "川島旅館,https://www.jalan.net/yad386526/,care-private-openair\n"
        "ピリカ,https://www.jalan.net/yad377160/,\n",
        encoding="utf-8",
    )

    actual = load_preferred_options_by_name(file_path)

    assert actual == {
        "川島旅館": {
            PreferredOption.CARE_KAKENAGASHI,
            PreferredOption.CARE_BATH_RENT,
            PreferredOption.CARE_PRIVATE_OPENAIR,
        }
    }


def test_load_preferred_options_by_name_rejects_unsupported_token(tmp_path: Path) -> None:
    file_path = tmp_path / "candidates.csv"
    file_path.write_text(
        "宿名,URL,優先オプション\n"
        "川島旅館,https://www.jalan.net/yad386526/,invalid-option\n",
        encoding="utf-8",
    )

    with pytest.raises(InvalidPreferredOptionError) as error:
        load_preferred_options_by_name(file_path)

    assert "invalid-option" in str(error.value)
