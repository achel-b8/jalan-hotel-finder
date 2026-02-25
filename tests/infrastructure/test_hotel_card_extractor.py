from pathlib import Path

from jalan_hotel_finder.infrastructure.hotel_card_extractor import extract_hotel_cards_from_html


def _read_fixture(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_extracts_required_fields_from_normal_html() -> None:
    html = _read_fixture("tests/fixtures/html/hotel_cards_structured_and_dom.html")

    actual = extract_hotel_cards_from_html(html)

    assert len(actual) == 1
    assert actual[0]["hotel_name"] == "札幌温泉ホテル"
    assert actual[0]["hotel_url"] == "https://www.jalan.net/yad123456/"
    assert actual[0]["plan_name"] == "夕朝食付きプラン"
    assert actual[0]["price"] == 12300


def test_price_is_null_when_missing() -> None:
    html = _read_fixture("tests/fixtures/html/hotel_cards_dom_only_missing_price.html")

    actual = extract_hotel_cards_from_html(html)

    assert len(actual) == 1
    assert actual[0]["price"] is None


def test_fallback_does_not_crash_when_dom_is_partial() -> None:
    html = "<html><body><a href='/yad999999/'>宿だけ</a></body></html>"

    actual = extract_hotel_cards_from_html(html)

    assert len(actual) == 1
    assert actual[0]["hotel_name"] == "宿だけ"
    assert actual[0]["plan_name"] == "宿だけ"


def test_extracts_keyword_result_cards_from_open_yado_syosai_links() -> None:
    html = _read_fixture("tests/fixtures/html/hotel_cards_keyword_open_yado.html")

    actual = extract_hotel_cards_from_html(html)

    assert len(actual) == 1
    assert actual[0]["hotel_name"] == "ピリカレラホテル"
    assert actual[0]["hotel_url"] == "https://www.jalan.net/yad377160/"
    assert actual[0]["plan_name"].startswith("選べる夕食！鉄板フレンチ")
    assert actual[0]["price"] == 42900


def test_extracts_multiple_plan_rows_from_modern_result_item() -> None:
    html = _read_fixture("tests/fixtures/html/hotel_cards_modern_multiple_plans.html")

    actual = extract_hotel_cards_from_html(html)

    assert len(actual) == 3
    assert [record["hotel_url"] for record in actual] == [
        "https://www.jalan.net/yad777777/",
        "https://www.jalan.net/yad777777/",
        "https://www.jalan.net/yad777777/",
    ]
    assert [record["plan_name"] for record in actual] == ["プランA", "プランB", "プランC"]
    assert [record["price"] for record in actual] == [10000, 12000, 14000]


def test_ignores_faq_noise_links_from_search_page() -> None:
    html = _read_fixture("tests/fixtures/html/hotel_cards_faq_noise_only.html")

    actual = extract_hotel_cards_from_html(html)

    assert actual == []


def test_extracts_coupon_uww1405_cards_by_yad_no_links() -> None:
    html = _read_fixture("tests/fixtures/html/hotel_cards_coupon_uww1405.html")

    actual = extract_hotel_cards_from_html(html)

    assert len(actual) == 3
    assert [record["hotel_name"] for record in actual] == [
        "札幌グランドホテル",
        "札幌グランドホテル",
        "ホテルエミシア札幌",
    ]
    assert [record["hotel_url"] for record in actual] == [
        "https://www.jalan.net/yad321756/",
        "https://www.jalan.net/yad321756/",
        "https://www.jalan.net/yad338679/",
    ]
    assert [record["plan_name"] for record in actual] == [
        "朝食付きプラン",
        "素泊まりプラン",
        "夕朝食付きプラン",
    ]
    assert [record["price"] for record in actual] == [21250, 27000, 18600]
