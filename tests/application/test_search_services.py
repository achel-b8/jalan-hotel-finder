from pathlib import Path
from typing import Any

import pytest

from jalan_hotel_finder.application.input_models import SearchAreaInput, SearchNamesInput
from jalan_hotel_finder.application.search_services import (
    AreaSearchFailedError,
    FetchedPage,
    search_area,
    search_names_local_filter,
)


class _FakeCrawler:
    def __init__(self, html_by_url: dict[str, str], error_urls: set[str] | None = None) -> None:
        self._html_by_url = html_by_url
        self._error_urls = error_urls or set()
        self.sleep_calls = 0

    async def fetch_url(self, url: str) -> FetchedPage:
        if url in self._error_urls:
            raise TimeoutError("network timeout")
        html = self._html_by_url.get(url, "")
        return FetchedPage(url=url, html=html, status_code=200)

    async def sleep_between_areas(self) -> None:
        self.sleep_calls += 1


def _resolver(prefecture_name: str) -> list[str]:
    if prefecture_name == "北海道":
        return ["SML_010202"]
    if prefecture_name == "青森県":
        return ["SML_020202"]
    raise ValueError("unknown prefecture")


def _extractor_from_marker(html: str) -> list[dict[str, Any]]:
    if html == "area1":
        return [
            {
                "hotel_name": "札幌温泉ホテル",
                "hotel_url": "https://www.jalan.net/yad123456/?plan=first",
                "plan_name": "先勝ちプラン",
                "price": 12000,
            }
        ]
    if html == "area2":
        return [
            {
                "hotel_name": "札幌温泉ホテル",
                "hotel_url": "https://www.jalan.net/yad123456/?plan=second",
                "plan_name": "後勝ちプラン",
                "price": 9000,
            }
        ]
    return []


@pytest.mark.asyncio
async def test_search_area_deduplicates_across_multiple_sml() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10", pref=["北海道", "青森県"])
    html_by_url = {
        "https://www.jalan.net/010000/LRG_010200/SML_010202/?stayYear=2026&stayMonth=03&stayDay=10&adultNum=1&stayCount=1&mealType=3&roomCount=1&dateUndecided=0&careBath=0&careKake=1": "area1",
        "https://www.jalan.net/020000/LRG_020200/SML_020202/?stayYear=2026&stayMonth=03&stayDay=10&adultNum=1&stayCount=1&mealType=3&roomCount=1&dateUndecided=0&careBath=0&careKake=1": "area2",
    }
    crawler = _FakeCrawler(html_by_url=html_by_url)

    actual = await search_area(
        user_input=user_input,
        resolve_sml_codes_for_prefecture=_resolver,
        crawler=crawler,
        hotel_card_extractor=_extractor_from_marker,
        next_page_extractor=lambda html, url: None,
    )

    assert len(actual) == 1
    assert actual[0]["plan_name"] == "先勝ちプラン"
    assert actual[0]["hotel_url_normalized"] == "/yad123456"


@pytest.mark.asyncio
async def test_search_area_raises_when_one_area_fails() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10", pref=["北海道"])
    target_url = "https://www.jalan.net/010000/LRG_010200/SML_010202/?stayYear=2026&stayMonth=03&stayDay=10&adultNum=1&stayCount=1&mealType=3&roomCount=1&dateUndecided=0&careBath=0&careKake=1"
    crawler = _FakeCrawler(html_by_url={}, error_urls={target_url})

    with pytest.raises(AreaSearchFailedError):
        await search_area(
            user_input=user_input,
            resolve_sml_codes_for_prefecture=_resolver,
            crawler=crawler,
            hotel_card_extractor=_extractor_from_marker,
            next_page_extractor=lambda html, url: None,
        )


@pytest.mark.asyncio
async def test_search_area_returns_empty_when_no_records() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10", pref=["北海道"])
    url = "https://www.jalan.net/010000/LRG_010200/SML_010202/?stayYear=2026&stayMonth=03&stayDay=10&adultNum=1&stayCount=1&mealType=3&roomCount=1&dateUndecided=0&careBath=0&careKake=1"
    crawler = _FakeCrawler(html_by_url={url: "empty"})

    actual = await search_area(
        user_input=user_input,
        resolve_sml_codes_for_prefecture=_resolver,
        crawler=crawler,
        hotel_card_extractor=lambda html: [],
        next_page_extractor=lambda html, url: None,
    )

    assert actual == []


@pytest.mark.asyncio
async def test_search_names_local_filter_keeps_partial_matches_only(tmp_path: Path) -> None:
    names_file = tmp_path / "names.txt"
    names_file.write_text("札幌\n函館\n", encoding="utf-8")

    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )
    crawler = _FakeCrawler(html_by_url={})

    async def area_search_stub(
        user_input: SearchAreaInput,
        resolve_sml_codes_for_prefecture,
        crawler,
    ) -> list[dict[str, Any]]:
        return [
            {
                "hotel_name": "札幌温泉ホテル",
                "hotel_url": "https://www.jalan.net/yad111111/",
                "plan_name": "夕朝食付き",
                "price": 14000,
            },
            {
                "hotel_name": "小樽ベイホテル",
                "hotel_url": "https://www.jalan.net/yad222222/",
                "plan_name": "素泊まり",
                "price": 9000,
            },
        ]

    actual = await search_names_local_filter(
        user_input=user_input,
        resolve_sml_codes_for_prefecture=_resolver,
        crawler=crawler,
        names_loader=lambda _: ["札幌", "函館"],
        area_search_runner=area_search_stub,
    )

    assert len(actual) == 1
    assert actual[0]["hotel_name"] == "札幌温泉ホテル"
    assert actual[0]["matched_name"] == "札幌"
    assert actual[0]["search_type"] == "name"


@pytest.mark.asyncio
async def test_search_names_local_filter_returns_empty_when_no_match(tmp_path: Path) -> None:
    names_file = tmp_path / "names.txt"
    names_file.write_text("函館\n", encoding="utf-8")

    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )

    async def area_search_stub(
        user_input: SearchAreaInput,
        resolve_sml_codes_for_prefecture,
        crawler,
    ) -> list[dict[str, Any]]:
        return [
            {
                "hotel_name": "小樽ベイホテル",
                "hotel_url": "https://www.jalan.net/yad222222/",
                "plan_name": "素泊まり",
                "price": 9000,
                "search_type": "area",
                "area": "SML_010202",
            }
        ]

    actual = await search_names_local_filter(
        user_input=user_input,
        resolve_sml_codes_for_prefecture=_resolver,
        crawler=_FakeCrawler(html_by_url={}),
        names_loader=lambda _: ["函館"],
        area_search_runner=area_search_stub,
    )

    assert actual == []


@pytest.mark.asyncio
async def test_search_names_local_filter_keeps_deduplication_after_match(tmp_path: Path) -> None:
    names_file = tmp_path / "names.txt"
    names_file.write_text("札幌\n", encoding="utf-8")

    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )

    async def _search_area_stub(
        user_input: SearchAreaInput,
        resolve_sml_codes_for_prefecture,
        crawler,
    ) -> list[dict[str, Any]]:
        return [
            {
                "hotel_name": "札幌温泉ホテル",
                "hotel_url": "https://www.jalan.net/yad111111/?plan=1",
                "plan_name": "プラン1",
                "price": 10000,
                "search_type": "area",
                "area": "SML_010202",
            },
            {
                "hotel_name": "札幌温泉ホテル",
                "hotel_url": "https://www.jalan.net/yad111111/?plan=2",
                "plan_name": "プラン2",
                "price": 12000,
                "search_type": "area",
                "area": "SML_010202",
            },
        ]

    actual = await search_names_local_filter(
        user_input=user_input,
        resolve_sml_codes_for_prefecture=_resolver,
        crawler=_FakeCrawler(html_by_url={}),
        names_loader=lambda _: ["札幌"],
        area_search_runner=_search_area_stub,
    )

    assert len(actual) == 1
    assert actual[0]["hotel_url_normalized"] == "/yad111111"
