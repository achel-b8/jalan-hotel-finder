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


def test_ignores_faq_noise_links_from_search_page() -> None:
    html = _read_fixture("tests/fixtures/html/hotel_cards_faq_noise_only.html")

    actual = extract_hotel_cards_from_html(html)

    assert actual == []
