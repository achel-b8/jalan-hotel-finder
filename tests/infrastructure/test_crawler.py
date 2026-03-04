import asyncio

import pytest

from jalan_hotel_finder.infrastructure.access_control import (
    AccessRestrictedError,
    InvalidAreaRouteError,
)
from jalan_hotel_finder.infrastructure.crawler import (
    CrawlFetchError,
    FetchResult,
    PlaywrightCrawler,
)


class _CountingFetcher:
    def __init__(self, delay_sec: float = 0.02) -> None:
        self._delay_sec = delay_sec
        self.current_concurrency = 0
        self.max_concurrency = 0

    async def fetch(self, url: str) -> FetchResult:
        self.current_concurrency += 1
        self.max_concurrency = max(self.max_concurrency, self.current_concurrency)
        try:
            await asyncio.sleep(self._delay_sec)
            return FetchResult(url=url, html="<a href='/yad123456/'>hotel</a>", status_code=200)
        finally:
            self.current_concurrency -= 1


class _TimeoutFetcher:
    async def fetch(self, url: str) -> FetchResult:
        raise asyncio.TimeoutError("timeout")


class _RestrictedFetcher:
    def __init__(self) -> None:
        self.called_urls: list[str] = []

    async def fetch(self, url: str) -> FetchResult:
        self.called_urls.append(url)
        if "blocked" in url:
            return FetchResult(
                url=url,
                html="ただいまアクセスが集中しています。しばらく時間をおいてください",
                status_code=200,
            )
        return FetchResult(url=url, html="<a href='/yad999999/'>hotel</a>", status_code=200)


class _InvalidAreaRouteFetcher:
    async def fetch(self, url: str) -> FetchResult:
        return FetchResult(
            url=url,
            html=(
                "<title>エラー画面</title>"
                "ただ今の時間帯アクセスが集中しているため、つながりにくくなっております。"
            ),
            status_code=200,
        )


@pytest.mark.asyncio
async def test_parallel_limit_is_respected_with_semaphore() -> None:
    fetcher = _CountingFetcher()
    crawler = PlaywrightCrawler(fetcher=fetcher, parallel=2)

    urls = [f"https://example.com/{index}" for index in range(8)]
    await crawler.fetch_urls(urls)

    assert fetcher.max_concurrency <= 2


@pytest.mark.asyncio
async def test_timeout_is_converted_to_crawl_fetch_error() -> None:
    crawler = PlaywrightCrawler(fetcher=_TimeoutFetcher(), parallel=1)

    with pytest.raises(CrawlFetchError):
        await crawler.fetch_url("https://example.com/timeout")


@pytest.mark.asyncio
async def test_access_restriction_stops_before_next_area_batch() -> None:
    fetcher = _RestrictedFetcher()
    crawler = PlaywrightCrawler(fetcher=fetcher, parallel=2)

    with pytest.raises(AccessRestrictedError):
        await crawler.fetch_area_batches(
            {
                "SML_010202": ["https://example.com/blocked"],
                "SML_010205": ["https://example.com/should-not-run"],
            }
        )

    assert "https://example.com/should-not-run" not in fetcher.called_urls


@pytest.mark.asyncio
async def test_invalid_area_route_error_is_raised_for_sml_error_template() -> None:
    crawler = PlaywrightCrawler(fetcher=_InvalidAreaRouteFetcher(), parallel=1)

    with pytest.raises(InvalidAreaRouteError):
        await crawler.fetch_url("https://www.jalan.net/100000/LRG_101400/SML_101402/")
