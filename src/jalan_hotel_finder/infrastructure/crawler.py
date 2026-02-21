"""Crawler infrastructure with Playwright fetcher and concurrency control."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Protocol

from jalan_hotel_finder.infrastructure.access_control import (
    AccessRestrictedError,
    raise_if_access_restricted,
)


_HOTEL_LINK_PATTERN = re.compile(r"/yad\d+/?")


@dataclass(slots=True)
class FetchResult:
    """Fetched page payload used by application services."""

    url: str
    html: str
    status_code: int | None


class PageTimeoutError(RuntimeError):
    """Raised by low-level fetchers when a page load times out."""


class CrawlFetchError(RuntimeError):
    """Raised when a fetch cannot be completed in crawler orchestration."""


class AsyncPageFetcher(Protocol):
    """Abstract asynchronous fetcher used by PlaywrightCrawler."""

    async def fetch(self, url: str) -> FetchResult:
        """Fetch one URL and return HTML/status."""


class PlaywrightPageFetcher:
    """Playwright-backed page fetcher for real execution."""

    def __init__(self, page_load_timeout_ms: int = 30_000, headless: bool = True) -> None:
        self._page_load_timeout_ms = page_load_timeout_ms
        self._headless = headless
        self._playwright = None
        self._browser = None

    async def __aenter__(self) -> "PlaywrightPageFetcher":
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def fetch(self, url: str) -> FetchResult:
        if self._browser is None:
            raise RuntimeError("PlaywrightPageFetcher must be used as an async context manager")

        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        page = await self._browser.new_page()
        page.set_default_timeout(self._page_load_timeout_ms)

        try:
            response = await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            status_code = response.status if response is not None else None
            return FetchResult(url=url, html=html, status_code=status_code)
        except PlaywrightTimeoutError as error:
            raise PageTimeoutError(f"timeout while loading URL: {url}") from error
        finally:
            await page.close()


class PlaywrightCrawler:
    """Concurrency control and error policy around page fetching."""

    def __init__(
        self,
        fetcher: AsyncPageFetcher,
        parallel: int = 2,
        area_delay_ms: int = 1_000,
    ) -> None:
        if parallel < 1 or parallel > 10:
            raise ValueError("parallel must be between 1 and 10")

        self._fetcher = fetcher
        self._parallel = parallel
        self._area_delay_ms = area_delay_ms
        self._semaphore = asyncio.Semaphore(parallel)

    async def fetch_url(self, url: str) -> FetchResult:
        """Fetch one URL with semaphore and translate transient failures."""
        async with self._semaphore:
            try:
                fetched = await self._fetcher.fetch(url)
            except AccessRestrictedError:
                raise
            except (TimeoutError, asyncio.TimeoutError, PageTimeoutError) as error:
                raise CrawlFetchError(f"timeout while fetching URL: {url}") from error
            except Exception as error:
                raise CrawlFetchError(f"failed to fetch URL: {url}") from error

        hotel_link_count = len(_HOTEL_LINK_PATTERN.findall(fetched.html))
        raise_if_access_restricted(fetched.status_code, fetched.html, hotel_link_count)
        return fetched

    async def fetch_urls(self, urls: Sequence[str]) -> list[FetchResult]:
        """Fetch URLs concurrently under the configured semaphore."""
        tasks = [asyncio.create_task(self.fetch_url(url)) for url in urls]
        return await asyncio.gather(*tasks)

    async def fetch_area_batches(
        self,
        area_to_urls: Mapping[str, Sequence[str]],
    ) -> dict[str, list[FetchResult]]:
        """Fetch URL batches for each area with wait between areas."""
        output: dict[str, list[FetchResult]] = {}
        area_items = list(area_to_urls.items())

        for index, (area_code, urls) in enumerate(area_items):
            output[area_code] = await self.fetch_urls(urls)
            if index < len(area_items) - 1:
                await self.sleep_between_areas()

        return output

    async def sleep_between_areas(self) -> None:
        """Wait between areas according to v1 fixed policy."""
        await asyncio.sleep(self._area_delay_ms / 1000)
