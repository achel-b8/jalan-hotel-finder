from pathlib import Path

import pytest

from jalan_hotel_finder.application.input_models import SearchAreaInput, SearchNamesInput
from jalan_hotel_finder.application.search_services import (
    FetchedPage,
    search_area,
    search_names_keyword_one_shot,
)
from jalan_hotel_finder.application.query_builder import (
    build_keyword_search_url,
    build_search_area_url,
)
from jalan_hotel_finder.output.json_formatter import serialize_search_results


class _FakeCrawler:
    def __init__(self, html_by_url: dict[str, str]) -> None:
        self._html_by_url = html_by_url

    async def fetch_url(self, url: str) -> FetchedPage:
        html = self._html_by_url.get(url)
        if html is None:
            raise AssertionError(f"unexpected url: {url}")
        return FetchedPage(url=url, html=html, status_code=200)

    async def sleep_between_areas(self) -> None:
        return None


def _resolver(prefecture_name: str) -> list[str]:
    if prefecture_name == "北海道":
        return ["SML_010202"]
    raise ValueError(f"unknown prefecture: {prefecture_name}")


def _fixture(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_integration_us01_area_search_list_snapshot() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10", pref=["北海道"])
    start_url = build_search_area_url("SML_010202", user_input)
    second_url = "https://www.jalan.net/010000/LRG_010200/SML_010202/?idx=30"

    crawler = _FakeCrawler(
        {
            start_url: _fixture("tests/fixtures/html/integration/area_page1.html"),
            second_url: _fixture("tests/fixtures/html/integration/area_page2.html"),
        }
    )

    records = await search_area(
        user_input=user_input,
        resolve_sml_codes_for_prefecture=_resolver,
        crawler=crawler,
    )

    actual_output = serialize_search_results(records)
    expected_output = (
        "検索結果: 2件\n"
        "\n"
        "[1] 宿名: 札幌温泉ホテル\n"
        "URL: https://www.jalan.net/yad100000/\n"
        "  - プラン1: 夕朝食付き / 10,000円\n"
        "\n"
        "[2] 宿名: 函館シティホテル\n"
        "URL: https://www.jalan.net/yad200000/\n"
        "  - プラン1: 朝食付き / 12,000円"
    )

    assert actual_output == expected_output


@pytest.mark.asyncio
async def test_integration_us02_names_search_list_snapshot(tmp_path: Path) -> None:
    names_file = tmp_path / "names.txt"
    names_file.write_text("札幌\n", encoding="utf-8")

    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )
    start_url = build_keyword_search_url("札幌", user_input.keyword_encoding)

    crawler = _FakeCrawler(
        {
            start_url: _fixture("tests/fixtures/html/integration/names_page.html"),
        }
    )

    records = await search_names_keyword_one_shot(
        user_input=user_input,
        crawler=crawler,
        names_loader=lambda _: ["札幌"],
    )

    actual_output = serialize_search_results(records)
    expected_output = (
        "検索結果: 1件\n"
        "\n"
        "[1] 宿名: 札幌温泉ホテル\n"
        "URL: https://www.jalan.net/yad100000/\n"
        "  - プラン1: 夕朝食付き / 10,000円"
    )
    assert actual_output == expected_output
