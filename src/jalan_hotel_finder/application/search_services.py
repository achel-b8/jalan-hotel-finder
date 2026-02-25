"""Application services for `area`, `list`, and `coupon` use cases."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Protocol

from jalan_hotel_finder.application.input_models import (
    SearchAreaInput,
    SearchCouponInput,
    SearchNamesInput,
)
from jalan_hotel_finder.application.pagination import (
    extract_next_page_url_from_html,
    normalize_page_url,
    should_continue_pagination,
)
from jalan_hotel_finder.application.query_builder import (
    build_coupon_search_url,
    build_keyword_search_url,
    build_search_area_url,
)
from jalan_hotel_finder.domain.hotel_deduplication import (
    deduplicate_hotels_by_normalized_url,
)
from jalan_hotel_finder.domain.name_matching import (
    PreferredOption,
    filter_hotels_by_names,
    load_hotel_names,
    load_preferred_options_by_name,
)
from jalan_hotel_finder.infrastructure.hotel_card_extractor import extract_hotel_cards_from_html

_HOTEL_URL_TARGET_PATTERN = re.compile(r"/yad\d+", re.IGNORECASE)


class AreaSearchFailedError(RuntimeError):
    """Raised when one area fails and stop policy aborts execution."""

    def __init__(self, area_code: str, failed_url: str, reason: str) -> None:
        self.area_code = area_code
        self.failed_url = failed_url
        message = f"area fetch failed: area={area_code} url={failed_url} reason={reason}"
        super().__init__(message)


class NameSearchFailedError(RuntimeError):
    """Raised when one keyword fetch fails in `list` command."""

    def __init__(self, keyword: str, failed_url: str, reason: str) -> None:
        self.keyword = keyword
        self.failed_url = failed_url
        message = f"name fetch failed: keyword={keyword} url={failed_url} reason={reason}"
        super().__init__(message)


class CouponSearchFailedError(RuntimeError):
    """Raised when one coupon area fetch fails in `coupon` command."""

    def __init__(self, lrg_code: str, failed_url: str, reason: str) -> None:
        self.lrg_code = lrg_code
        self.failed_url = failed_url
        message = f"coupon fetch failed: area={lrg_code} url={failed_url} reason={reason}"
        super().__init__(message)


@dataclass(slots=True)
class FetchedPage:
    """Minimal page payload consumed by application services."""

    url: str
    html: str
    status_code: int | None


class CrawlerPort(Protocol):
    """Crawler port used by application services."""

    async def fetch_url(self, url: str) -> FetchedPage:
        """Fetch one URL and return the page payload."""

    async def sleep_between_areas(self) -> None:
        """Wait between areas."""


async def search_area(
    user_input: SearchAreaInput,
    resolve_sml_codes_for_prefecture: Callable[[str], list[str]],
    crawler: CrawlerPort,
    hotel_card_extractor: Callable[[str], list[dict[str, Any]]] = extract_hotel_cards_from_html,
    next_page_extractor: Callable[[str, str], str | None] = extract_next_page_url_from_html,
) -> list[dict[str, Any]]:
    """Run area search flow and return deduplicated records."""
    area_codes = _expand_sml_area_codes(user_input, resolve_sml_codes_for_prefecture)
    if not area_codes:
        return []

    collected_records: list[dict[str, Any]] = []

    for area_index, area_code in enumerate(area_codes):
        start_url = build_search_area_url(area_code, user_input)
        current_url: str | None = start_url
        visited_urls: set[str] = set()

        while current_url is not None:
            normalized_current = normalize_page_url(current_url)
            if normalized_current in visited_urls:
                break
            visited_urls.add(normalized_current)

            try:
                fetched_page = await crawler.fetch_url(current_url)
            except Exception as error:  # stop policy: 1 area failure aborts whole command
                raise AreaSearchFailedError(area_code, current_url, str(error)) from error

            extracted_records = hotel_card_extractor(fetched_page.html)
            for record in extracted_records:
                normalized_record = dict(record)
                normalized_record["search_type"] = "area"
                normalized_record["area"] = area_code
                collected_records.append(normalized_record)

            next_url = next_page_extractor(fetched_page.html, current_url)
            if not should_continue_pagination(next_url, visited_urls):
                break

            current_url = next_url

        if area_index < len(area_codes) - 1:
            await crawler.sleep_between_areas()

    return deduplicate_hotels_by_normalized_url(collected_records)


async def search_names_local_filter(
    user_input: SearchNamesInput,
    resolve_sml_codes_for_prefecture: Callable[[str], list[str]],
    crawler: CrawlerPort,
    names_loader: Callable[[Path], list[str]] = load_hotel_names,
    area_search_runner: Callable[
        [SearchAreaInput, Callable[[str], list[str]], CrawlerPort],
        Awaitable[list[dict[str, Any]]],
    ] = search_area,
) -> list[dict[str, Any]]:
    """Run `area` flow then apply local partial-match filtering for `list`."""
    target_names = names_loader(user_input.names_file)

    area_input = SearchAreaInput(
        checkin=user_input.checkin,
        pref=user_input.pref,
        adults=user_input.adults,
        nights=user_input.nights,
        max_price=user_input.max_price,
        meal_type=user_input.meal_type,
        parallel=user_input.parallel,
    )

    area_results = await area_search_runner(
        user_input=area_input,
        resolve_sml_codes_for_prefecture=resolve_sml_codes_for_prefecture,
        crawler=crawler,
    )

    matched = filter_hotels_by_names(area_results, target_names)
    for record in matched:
        record["search_type"] = "name"

    return deduplicate_hotels_by_normalized_url(matched)


async def search_names_keyword_one_shot(
    user_input: SearchNamesInput,
    crawler: CrawlerPort,
    names_loader: Callable[[Path], list[str]] = load_hotel_names,
    keyword_options_loader: Callable[
        [Path],
        dict[str, set[PreferredOption]],
    ] = load_preferred_options_by_name,
    hotel_card_extractor: Callable[[str], list[dict[str, Any]]] = extract_hotel_cards_from_html,
) -> list[dict[str, Any]]:
    """Run one-shot keyword search for each candidate name (no pagination)."""
    target_names = names_loader(user_input.names_file)
    keyword_options_by_name = keyword_options_loader(user_input.names_file)
    keyword_targets = _extract_keyword_targets(target_names)
    if not keyword_targets:
        return []

    tasks = [
        asyncio.create_task(
            _fetch_one_keyword(
                keyword=keyword,
                user_input=user_input,
                preferred_options=keyword_options_by_name.get(keyword, set()),
                crawler=crawler,
                hotel_card_extractor=hotel_card_extractor,
            )
        )
        for keyword in keyword_targets
    ]
    fetched_by_keyword = await asyncio.gather(*tasks)

    all_records = [record for batch in fetched_by_keyword for record in batch]
    matched = filter_hotels_by_names(all_records, target_names)
    for record in matched:
        record["search_type"] = "name"
    return deduplicate_hotels_by_normalized_url(matched)


async def search_coupon(
    user_input: SearchCouponInput,
    resolve_coupon_id: Callable[[str, str], str],
    resolve_lrg_codes_for_prefecture: Callable[[str], list[str]],
    crawler: CrawlerPort,
    hotel_card_extractor: Callable[[str], list[dict[str, Any]]] = extract_hotel_cards_from_html,
    next_page_extractor: Callable[[str, str], str | None] = extract_next_page_url_from_html,
) -> list[dict[str, Any]]:
    """Run coupon-target hotel search flow and return deduplicated records."""
    coupon_id = resolve_coupon_id(
        user_input.coupon_name,
        str(user_input.coupon_source_url),
    )
    lrg_codes = _expand_lrg_area_codes(user_input, resolve_lrg_codes_for_prefecture)
    if not lrg_codes:
        return []

    collected_records: list[dict[str, Any]] = []

    for lrg_index, lrg_code in enumerate(lrg_codes):
        start_url = build_coupon_search_url(
            lrg_code=lrg_code,
            user_input=user_input,
            coupon_id=coupon_id,
            idx=0,
        )
        current_url: str | None = start_url
        visited_urls: set[str] = set()

        while current_url is not None:
            normalized_current = normalize_page_url(current_url)
            if normalized_current in visited_urls:
                break
            visited_urls.add(normalized_current)

            try:
                fetched_page = await crawler.fetch_url(current_url)
            except Exception as error:
                raise CouponSearchFailedError(lrg_code, current_url, str(error)) from error

            extracted_records = hotel_card_extractor(fetched_page.html)
            for record in extracted_records:
                normalized_record = dict(record)
                normalized_record["search_type"] = "coupon"
                normalized_record["area"] = lrg_code
                normalized_record["coupon_id"] = coupon_id
                collected_records.append(normalized_record)

            next_url = next_page_extractor(fetched_page.html, current_url)
            if not should_continue_pagination(next_url, visited_urls):
                break
            current_url = next_url

        if lrg_index < len(lrg_codes) - 1:
            await crawler.sleep_between_areas()

    return deduplicate_hotels_by_normalized_url(collected_records)


def _expand_sml_area_codes(
    user_input: SearchAreaInput,
    resolve_sml_codes_for_prefecture: Callable[[str], list[str]],
) -> list[str]:
    area_codes: list[str] = []
    seen: set[str] = set()

    for prefecture_name in user_input.pref:
        for area_code in resolve_sml_codes_for_prefecture(prefecture_name):
            if area_code in seen:
                continue
            seen.add(area_code)
            area_codes.append(area_code)

    return area_codes


def _expand_lrg_area_codes(
    user_input: SearchCouponInput,
    resolve_lrg_codes_for_prefecture: Callable[[str], list[str]],
) -> list[str]:
    lrg_codes: list[str] = []
    seen: set[str] = set()

    for prefecture_name in user_input.pref:
        for lrg_code in resolve_lrg_codes_for_prefecture(prefecture_name):
            if lrg_code in seen:
                continue
            seen.add(lrg_code)
            lrg_codes.append(lrg_code)

    return lrg_codes


def _extract_keyword_targets(target_names: list[str]) -> list[str]:
    keyword_targets: list[str] = []
    seen: set[str] = set()

    for target in target_names:
        stripped = target.strip()
        if not stripped:
            continue
        if _HOTEL_URL_TARGET_PATTERN.search(stripped):
            continue
        if stripped in seen:
            continue
        seen.add(stripped)
        keyword_targets.append(stripped)

    return keyword_targets


async def _fetch_one_keyword(
    keyword: str,
    user_input: SearchNamesInput,
    preferred_options: set[PreferredOption],
    crawler: CrawlerPort,
    hotel_card_extractor: Callable[[str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    url = build_keyword_search_url(
        keyword,
        user_input.keyword_encoding,
        user_input.max_price,
        checkin=user_input.checkin,
        adults=user_input.adults,
        nights=user_input.nights,
        meal_type=user_input.meal_type,
        care_kakenagashi=PreferredOption.CARE_KAKENAGASHI in preferred_options,
        care_bath_rent=PreferredOption.CARE_BATH_RENT in preferred_options,
        care_private_openair=PreferredOption.CARE_PRIVATE_OPENAIR in preferred_options,
    )
    try:
        fetched_page = await crawler.fetch_url(url)
    except Exception as error:
        raise NameSearchFailedError(keyword, url, str(error)) from error

    extracted_records = hotel_card_extractor(fetched_page.html)
    normalized_records: list[dict[str, Any]] = []
    for record in extracted_records:
        normalized = dict(record)
        normalized["search_type"] = "name"
        normalized_records.append(normalized)
    return normalized_records
