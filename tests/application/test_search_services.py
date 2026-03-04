from pathlib import Path
from typing import Any

import pytest

from jalan_hotel_finder.application.area_routes import AreaRoute
from jalan_hotel_finder.application.input_models import (
    SearchAreaInput,
    SearchCouponInput,
    SearchNamesInput,
)
from jalan_hotel_finder.application.query_builder import (
    build_coupon_search_url,
    build_keyword_search_url,
)
from jalan_hotel_finder.application.search_services import (
    AreaSearchFailedError,
    CouponSearchFailedError,
    FetchedPage,
    search_coupon,
    search_area,
    search_names_keyword_one_shot,
    search_names_local_filter,
)
from jalan_hotel_finder.domain.name_matching import InvalidPreferredOptionError


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


class _TrackingCrawler:
    def __init__(self, html_by_url: dict[str, str]) -> None:
        self._html_by_url = html_by_url
        self.called_urls: list[str] = []

    async def fetch_url(self, url: str) -> FetchedPage:
        self.called_urls.append(url)
        return FetchedPage(url=url, html=self._html_by_url[url], status_code=200)

    async def sleep_between_areas(self) -> None:
        return None


def _build_area_route(
    pref_code: str,
    lrg_code: str,
    sml_code: str,
    pref_name: str,
) -> AreaRoute:
    return AreaRoute(
        pref_code=pref_code,
        lrg_code=lrg_code,
        sml_code=sml_code,
        pref_name=pref_name,
        lrg_name="テスト大エリア",
        sml_name="テスト小エリア",
    )


def _resolver(prefecture_name: str) -> list[AreaRoute]:
    if prefecture_name == "北海道":
        return [
            _build_area_route(
                pref_code="010000",
                lrg_code="LRG_010200",
                sml_code="SML_010202",
                pref_name="北海道",
            )
        ]
    if prefecture_name == "青森県":
        return [
            _build_area_route(
                pref_code="020000",
                lrg_code="LRG_020200",
                sml_code="SML_020202",
                pref_name="青森県",
            )
        ]
    raise ValueError("unknown prefecture")


def _lrg_resolver(prefecture_name: str) -> list[str]:
    if prefecture_name == "北海道":
        return ["LRG_010200"]
    if prefecture_name == "青森県":
        return ["LRG_020200"]
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
async def test_search_area_keeps_up_to_three_plans_per_hotel_across_multiple_sml() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10", pref=["北海道", "青森県"])
    html_by_url = {
        "https://www.jalan.net/010000/LRG_010200/SML_010202/?stayYear=2026&stayMonth=03&stayDay=10&adultNum=1&stayCount=1&roomCount=1&dateUndecided=0&careBath=0&careKake=1": "area1",
        "https://www.jalan.net/020000/LRG_020200/SML_020202/?stayYear=2026&stayMonth=03&stayDay=10&adultNum=1&stayCount=1&roomCount=1&dateUndecided=0&careBath=0&careKake=1": "area2",
    }
    crawler = _FakeCrawler(html_by_url=html_by_url)

    actual = await search_area(
        user_input=user_input,
        resolve_area_routes_for_prefecture=_resolver,
        crawler=crawler,
        hotel_card_extractor=_extractor_from_marker,
        next_page_extractor=lambda html, url: None,
    )

    assert len(actual) == 2
    assert actual[0]["plan_name"] == "先勝ちプラン"
    assert actual[1]["plan_name"] == "後勝ちプラン"
    assert actual[0]["hotel_url_normalized"] == "/yad123456"
    assert actual[1]["hotel_url_normalized"] == "/yad123456"


@pytest.mark.asyncio
async def test_search_area_raises_when_one_area_fails() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10", pref=["北海道"])
    target_url = "https://www.jalan.net/010000/LRG_010200/SML_010202/?stayYear=2026&stayMonth=03&stayDay=10&adultNum=1&stayCount=1&roomCount=1&dateUndecided=0&careBath=0&careKake=1"
    crawler = _FakeCrawler(html_by_url={}, error_urls={target_url})

    with pytest.raises(AreaSearchFailedError):
        await search_area(
            user_input=user_input,
            resolve_area_routes_for_prefecture=_resolver,
            crawler=crawler,
            hotel_card_extractor=_extractor_from_marker,
            next_page_extractor=lambda html, url: None,
        )


@pytest.mark.asyncio
async def test_search_area_returns_empty_when_no_records() -> None:
    user_input = SearchAreaInput(checkin="2026-03-10", pref=["北海道"])
    url = "https://www.jalan.net/010000/LRG_010200/SML_010202/?stayYear=2026&stayMonth=03&stayDay=10&adultNum=1&stayCount=1&roomCount=1&dateUndecided=0&careBath=0&careKake=1"
    crawler = _FakeCrawler(html_by_url={url: "empty"})

    actual = await search_area(
        user_input=user_input,
        resolve_area_routes_for_prefecture=_resolver,
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
        resolve_area_routes_for_prefecture,
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
        resolve_area_routes_for_prefecture=_resolver,
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
        resolve_area_routes_for_prefecture,
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
        resolve_area_routes_for_prefecture=_resolver,
        crawler=_FakeCrawler(html_by_url={}),
        names_loader=lambda _: ["函館"],
        area_search_runner=area_search_stub,
    )

    assert actual == []


@pytest.mark.asyncio
async def test_search_names_local_filter_keeps_up_to_three_plans_after_match(
    tmp_path: Path,
) -> None:
    names_file = tmp_path / "names.txt"
    names_file.write_text("札幌\n", encoding="utf-8")

    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )

    async def _search_area_stub(
        user_input: SearchAreaInput,
        resolve_area_routes_for_prefecture,
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
        resolve_area_routes_for_prefecture=_resolver,
        crawler=_FakeCrawler(html_by_url={}),
        names_loader=lambda _: ["札幌"],
        area_search_runner=_search_area_stub,
    )

    assert len(actual) == 2
    assert actual[0]["hotel_url_normalized"] == "/yad111111"
    assert actual[1]["hotel_url_normalized"] == "/yad111111"


@pytest.mark.asyncio
async def test_search_names_local_filter_accepts_hotel_url_candidates(tmp_path: Path) -> None:
    names_file = tmp_path / "candidate_hotels.csv"
    names_file.write_text(
        "宿名,URL,優先オプション\n"
        "候補その1,https://www.jalan.net/yad386526/?yadNo=386526&convertedFlg=1&ccnt=link-yad-386526-%E5%B7%9D%E5%B3%B6%E6%97%85%E9%A4%A8-0,care-kakenagashi\n"
        "候補その2,https://www.jalan.net/yad377160/?yadNo=377160&convertedFlg=1&ccnt=link-yad-377160-%E3%83%94%E3%83%AA%E3%82%AB-0,\n",
        encoding="utf-8",
    )

    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )

    async def area_search_stub(
        user_input: SearchAreaInput,
        resolve_area_routes_for_prefecture,
        crawler,
    ) -> list[dict[str, Any]]:
        return [
            {
                "hotel_name": "川島旅館",
                "hotel_url": "https://www.jalan.net/yad386526/?plan=1",
                "plan_name": "プラン1",
                "price": 10000,
                "search_type": "area",
                "area": "SML_010202",
            },
            {
                "hotel_name": "ピリカ",
                "hotel_url": "https://www.jalan.net/yad377160/?plan=1",
                "plan_name": "プラン2",
                "price": 12000,
                "search_type": "area",
                "area": "SML_010202",
            },
            {
                "hotel_name": "小樽ベイホテル",
                "hotel_url": "https://www.jalan.net/yad222222/?plan=1",
                "plan_name": "プラン3",
                "price": 9000,
                "search_type": "area",
                "area": "SML_010202",
            },
        ]

    actual = await search_names_local_filter(
        user_input=user_input,
        resolve_area_routes_for_prefecture=_resolver,
        crawler=_FakeCrawler(html_by_url={}),
        area_search_runner=area_search_stub,
    )

    assert len(actual) == 2
    assert actual[0]["hotel_name"] == "川島旅館"
    assert actual[0]["search_type"] == "name"
    assert actual[0]["matched_name"].startswith("https://www.jalan.net/yad386526/")
    assert actual[1]["hotel_name"] == "ピリカ"
    assert actual[1]["search_type"] == "name"
    assert actual[1]["matched_name"].startswith("https://www.jalan.net/yad377160/")


@pytest.mark.asyncio
async def test_search_names_keyword_one_shot_fetches_each_keyword_once(tmp_path: Path) -> None:
    names_file = tmp_path / "candidate_hotels.csv"
    names_file.write_text(
        "宿名,URL,優先オプション\n"
        "候補その1,https://www.jalan.net/yad386526/?yadNo=386526,\n"
        "候補その2,https://www.jalan.net/yad377160/?yadNo=377160,\n",
        encoding="utf-8",
    )
    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )
    keyword_url_1 = build_keyword_search_url(
        "川島旅館",
        user_input.keyword_encoding,
        checkin=user_input.checkin,
        adults=user_input.adults,
        nights=user_input.nights,
        meal_type=user_input.meal_type,
    )
    keyword_url_2 = build_keyword_search_url(
        "ピリカ",
        user_input.keyword_encoding,
        checkin=user_input.checkin,
        adults=user_input.adults,
        nights=user_input.nights,
        meal_type=user_input.meal_type,
    )
    crawler = _TrackingCrawler(
        {
            keyword_url_1: "kw1",
            keyword_url_2: "kw2",
        }
    )

    def _extractor(html: str) -> list[dict[str, Any]]:
        if html == "kw1":
            return [
                {
                    "hotel_name": "宿A",
                    "hotel_url": "https://www.jalan.net/yad386526/?plan=1",
                    "plan_name": "プランA",
                    "price": 10000,
                }
            ]
        if html == "kw2":
            return [
                {
                    "hotel_name": "宿B",
                    "hotel_url": "https://www.jalan.net/yad377160/?plan=1",
                    "plan_name": "プランB",
                    "price": 11000,
                }
            ]
        return []

    actual = await search_names_keyword_one_shot(
        user_input=user_input,
        crawler=crawler,
        names_loader=lambda _: [
            "川島旅館",
            "https://www.jalan.net/yad386526/?yadNo=386526",
            "ピリカ",
            "https://www.jalan.net/yad377160/?yadNo=377160",
        ],
        hotel_card_extractor=_extractor,
    )

    assert sorted(crawler.called_urls) == sorted([keyword_url_1, keyword_url_2])
    assert len(actual) == 2
    assert actual[0]["search_type"] == "name"
    assert actual[1]["search_type"] == "name"


@pytest.mark.asyncio
async def test_search_names_keyword_one_shot_passes_max_price_to_keyword_url(
    tmp_path: Path,
) -> None:
    names_file = tmp_path / "candidate_hotels.csv"
    names_file.write_text("宿名,URL,優先オプション\n", encoding="utf-8")
    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
        max_price=5000,
    )
    expected_url = build_keyword_search_url(
        "札幌",
        user_input.keyword_encoding,
        max_price=5000,
        checkin=user_input.checkin,
        adults=user_input.adults,
        nights=user_input.nights,
        meal_type=user_input.meal_type,
    )
    crawler = _TrackingCrawler({expected_url: "kw1"})

    actual = await search_names_keyword_one_shot(
        user_input=user_input,
        crawler=crawler,
        names_loader=lambda _: ["札幌"],
        hotel_card_extractor=lambda _: [],
    )

    assert actual == []
    assert crawler.called_urls == [expected_url]


@pytest.mark.asyncio
async def test_search_names_keyword_one_shot_returns_empty_when_only_url_candidates(
    tmp_path: Path,
) -> None:
    names_file = tmp_path / "candidate_hotels.csv"
    names_file.write_text("宿名,URL,優先オプション\n", encoding="utf-8")
    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )
    crawler = _TrackingCrawler({})

    actual = await search_names_keyword_one_shot(
        user_input=user_input,
        crawler=crawler,
        names_loader=lambda _: ["https://www.jalan.net/yad386526/?yadNo=386526"],
    )

    assert actual == []
    assert crawler.called_urls == []


@pytest.mark.asyncio
async def test_search_names_keyword_one_shot_uses_loaded_csv_candidates_for_url_match(
    tmp_path: Path,
) -> None:
    names_file = tmp_path / "candidate_hotels.csv"
    names_file.write_text(
        "宿名,URL,優先オプション\n"
        "川島旅館,https://www.jalan.net/yad386526/?yadNo=386526,\n"
        "ピリカ,https://www.jalan.net/yad377160/?yadNo=377160,\n",
        encoding="utf-8",
    )
    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )
    keyword_url_1 = build_keyword_search_url(
        "川島旅館",
        user_input.keyword_encoding,
        checkin=user_input.checkin,
        adults=user_input.adults,
        nights=user_input.nights,
        meal_type=user_input.meal_type,
    )
    keyword_url_2 = build_keyword_search_url(
        "ピリカ",
        user_input.keyword_encoding,
        checkin=user_input.checkin,
        adults=user_input.adults,
        nights=user_input.nights,
        meal_type=user_input.meal_type,
    )
    crawler = _TrackingCrawler(
        {
            keyword_url_1: "kw1",
            keyword_url_2: "kw2",
        }
    )

    def _extractor(html: str) -> list[dict[str, Any]]:
        if html == "kw1":
            return [
                {
                    "hotel_name": "宿A",
                    "hotel_url": "https://www.jalan.net/yad386526/?plan=1",
                    "plan_name": "プランA",
                    "price": 10000,
                }
            ]
        if html == "kw2":
            return [
                {
                    "hotel_name": "宿B",
                    "hotel_url": "https://www.jalan.net/yad377160/?plan=1",
                    "plan_name": "プランB",
                    "price": 11000,
                }
            ]
        return []

    actual = await search_names_keyword_one_shot(
        user_input=user_input,
        crawler=crawler,
        hotel_card_extractor=_extractor,
    )

    assert sorted(crawler.called_urls) == sorted([keyword_url_1, keyword_url_2])
    assert len(actual) == 2
    assert any(
        record["matched_name"].startswith("https://www.jalan.net/yad386526/")
        for record in actual
    )
    assert any(
        record["matched_name"].startswith("https://www.jalan.net/yad377160/")
        for record in actual
    )


@pytest.mark.asyncio
async def test_search_names_keyword_one_shot_applies_csv_preferred_options_to_keyword_url(
    tmp_path: Path,
) -> None:
    names_file = tmp_path / "candidate_hotels.csv"
    names_file.write_text(
        "宿名,URL,優先オプション\n"
        "川島旅館,https://www.jalan.net/yad386526/,care-kakenagashi|care-bath-rent\n",
        encoding="utf-8",
    )
    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )
    expected_url = build_keyword_search_url(
        "川島旅館",
        user_input.keyword_encoding,
        checkin=user_input.checkin,
        adults=user_input.adults,
        nights=user_input.nights,
        meal_type=user_input.meal_type,
        care_kakenagashi=True,
        care_bath_rent=True,
        care_private_openair=False,
    )
    crawler = _TrackingCrawler({expected_url: "kw1"})

    actual = await search_names_keyword_one_shot(
        user_input=user_input,
        crawler=crawler,
        hotel_card_extractor=lambda _: [],
    )

    assert actual == []
    assert crawler.called_urls == [expected_url]


@pytest.mark.asyncio
async def test_search_names_keyword_one_shot_raises_for_unsupported_csv_preferred_option(
    tmp_path: Path,
) -> None:
    names_file = tmp_path / "candidate_hotels.csv"
    names_file.write_text(
        "宿名,URL,優先オプション\n"
        "川島旅館,https://www.jalan.net/yad386526/,invalid-option\n",
        encoding="utf-8",
    )
    user_input = SearchNamesInput(
        names_file=names_file,
        checkin="2026-03-10",
        pref=["北海道"],
    )

    with pytest.raises(InvalidPreferredOptionError):
        await search_names_keyword_one_shot(
            user_input=user_input,
            crawler=_TrackingCrawler({}),
            hotel_card_extractor=lambda _: [],
        )


@pytest.mark.asyncio
async def test_search_coupon_keeps_up_to_three_plans_per_hotel_across_multiple_lrg() -> None:
    user_input = SearchCouponInput(
        coupon_name="【全国(対象施設のみ)】9,000円お得クーポン",
        coupon_source_url="https://www.jalan.net/discountCoupon/CAM1598252/",
        checkin="2026-03-10",
        pref=["北海道", "青森県"],
        adults=2,
    )
    coupon_id = "COU7128122"
    url1 = build_coupon_search_url("LRG_010200", user_input, coupon_id=coupon_id)
    url2 = build_coupon_search_url("LRG_020200", user_input, coupon_id=coupon_id)
    crawler = _FakeCrawler(
        html_by_url={
            url1: "area1",
            url2: "area2",
        }
    )

    actual = await search_coupon(
        user_input=user_input,
        resolve_coupon_id=lambda *_: coupon_id,
        resolve_lrg_codes_for_prefecture=_lrg_resolver,
        crawler=crawler,
        hotel_card_extractor=_extractor_from_marker,
        next_page_extractor=lambda html, url: None,
    )

    assert len(actual) == 2
    assert actual[0]["search_type"] == "coupon"
    assert actual[1]["search_type"] == "coupon"
    assert actual[0]["coupon_id"] == coupon_id
    assert actual[1]["coupon_id"] == coupon_id
    assert actual[0]["hotel_url_normalized"] == "/yad123456"
    assert actual[1]["hotel_url_normalized"] == "/yad123456"


@pytest.mark.asyncio
async def test_search_coupon_raises_when_one_area_fails() -> None:
    user_input = SearchCouponInput(
        coupon_name="【全国(対象施設のみ)】9,000円お得クーポン",
        coupon_source_url="https://www.jalan.net/discountCoupon/CAM1598252/",
        checkin="2026-03-10",
        pref=["北海道"],
        adults=2,
    )
    coupon_id = "COU7128122"
    target_url = build_coupon_search_url("LRG_010200", user_input, coupon_id=coupon_id)
    crawler = _FakeCrawler(html_by_url={}, error_urls={target_url})

    with pytest.raises(CouponSearchFailedError):
        await search_coupon(
            user_input=user_input,
            resolve_coupon_id=lambda *_: coupon_id,
            resolve_lrg_codes_for_prefecture=_lrg_resolver,
            crawler=crawler,
            hotel_card_extractor=_extractor_from_marker,
            next_page_extractor=lambda html, url: None,
        )


@pytest.mark.asyncio
async def test_search_coupon_returns_empty_when_no_records() -> None:
    user_input = SearchCouponInput(
        coupon_name="【全国(対象施設のみ)】9,000円お得クーポン",
        coupon_source_url="https://www.jalan.net/discountCoupon/CAM1598252/",
        checkin="2026-03-10",
        pref=["北海道"],
        adults=2,
    )
    coupon_id = "COU7128122"
    target_url = build_coupon_search_url("LRG_010200", user_input, coupon_id=coupon_id)
    crawler = _FakeCrawler(html_by_url={target_url: "empty"})

    actual = await search_coupon(
        user_input=user_input,
        resolve_coupon_id=lambda *_: coupon_id,
        resolve_lrg_codes_for_prefecture=_lrg_resolver,
        crawler=crawler,
        hotel_card_extractor=lambda _: [],
        next_page_extractor=lambda html, url: None,
    )

    assert actual == []


@pytest.mark.asyncio
async def test_search_coupon_follows_next_page_urls() -> None:
    user_input = SearchCouponInput(
        coupon_name="【全国(対象施設のみ)】9,000円お得クーポン",
        coupon_source_url="https://www.jalan.net/discountCoupon/CAM1598252/",
        checkin="2026-03-10",
        pref=["北海道"],
        adults=2,
    )
    coupon_id = "COU7128122"
    page1_url = build_coupon_search_url("LRG_010200", user_input, coupon_id=coupon_id, idx=0)
    page2_url = build_coupon_search_url("LRG_010200", user_input, coupon_id=coupon_id, idx=30)
    crawler = _TrackingCrawler({page1_url: "area1", page2_url: "area2"})

    actual = await search_coupon(
        user_input=user_input,
        resolve_coupon_id=lambda *_: coupon_id,
        resolve_lrg_codes_for_prefecture=_lrg_resolver,
        crawler=crawler,
        hotel_card_extractor=_extractor_from_marker,
        next_page_extractor=lambda html, _: page2_url if html == "area1" else None,
    )

    assert crawler.called_urls == [page1_url, page2_url]
    assert len(actual) == 2
