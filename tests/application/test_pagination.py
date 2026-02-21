from pathlib import Path

from jalan_hotel_finder.application.pagination import (
    build_next_page_url,
    extract_next_page_url_from_html,
    normalize_page_url,
    should_continue_pagination,
)


def _read_fixture(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_build_next_page_url_increments_by_30() -> None:
    current = "https://www.jalan.net/010000/LRG_010200/SML_010202/?idx=0"

    actual = build_next_page_url(current)

    assert "idx=30" in actual


def test_stops_when_next_page_link_is_missing() -> None:
    html = _read_fixture("tests/fixtures/html/pager_without_next.html")
    current = "https://www.jalan.net/010000/LRG_010200/SML_010202/?idx=0"

    next_url = extract_next_page_url_from_html(html, current)

    assert should_continue_pagination(next_url, set()) is False


def test_stops_when_same_url_reappears() -> None:
    html = _read_fixture("tests/fixtures/html/pager_with_next.html")
    current = "https://www.jalan.net/010000/LRG_010200/SML_010202/?idx=0"

    next_url = extract_next_page_url_from_html(html, current)
    assert next_url is not None

    visited = {normalize_page_url(next_url)}
    assert should_continue_pagination(next_url, visited) is False


def test_extract_next_page_url_ignores_idx_0_when_current_is_idx_0() -> None:
    html = '<html><body><a href="?idx=0">札幌</a></body></html>'
    current = "https://www.jalan.net/010000/LRG_010200/SML_010202/?idx=0"

    actual = extract_next_page_url_from_html(html, current)

    assert actual is None


def test_extract_next_page_url_prefers_smallest_offset_greater_than_current() -> None:
    html = """
    <html><body>
      <a href="?idx=60">3ページ目</a>
      <a href="?idx=30">2ページ目</a>
      <a href="?idx=0">1ページ目</a>
    </body></html>
    """
    current = "https://www.jalan.net/010000/LRG_010200/SML_010202/?idx=0"

    actual = extract_next_page_url_from_html(html, current)

    assert actual is not None
    assert "idx=30" in actual
