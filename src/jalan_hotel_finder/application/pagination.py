"""Pagination helpers for Jalan result pages."""

from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from selectolax.parser import HTMLParser


def build_next_page_url(current_url: str, step: int = 30) -> str:
    """Increment `idx`/`dispStartIndex` by one page."""
    parts = urlsplit(current_url)
    params = dict(parse_qsl(parts.query, keep_blank_values=True))

    offset_key = "dispStartIndex" if "dispStartIndex" in params else "idx"
    current_offset = int(params.get(offset_key, "0") or 0)
    params[offset_key] = str(current_offset + step)

    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment)
    )


def extract_next_page_url_from_html(html: str, current_url: str) -> str | None:
    """Find next-page URL from pager links, if present."""
    tree = HTMLParser(html)
    current_offset = _extract_offset_from_url(current_url)
    if current_offset is None:
        current_offset = 0

    candidates: list[tuple[int, str]] = []
    selector = (
        "nav.pagerLink a[href], "
        ".pagerLink a[href], "
        "a[rel='next'][href], "
        "a[aria-label*='次'][href], "
        "a[href*='idx='], "
        "a[href*='dispStartIndex=']"
    )

    for link in tree.css(selector):
        href = (link.attributes.get("href") or "").strip()
        if not href:
            continue

        next_url = urljoin(current_url, href)
        if normalize_page_url(next_url) == normalize_page_url(current_url):
            continue

        next_offset = _extract_offset_from_url(next_url)
        if next_offset is None:
            continue
        if next_offset <= current_offset:
            continue

        candidates.append((next_offset, next_url))

    if candidates:
        candidates.sort(key=lambda pair: pair[0])
        return candidates[0][1]

    return None


def normalize_page_url(url: str) -> str:
    """Canonicalize URL for cycle detection by sorting query params."""
    parts = urlsplit(url)
    sorted_params = sorted(parse_qsl(parts.query, keep_blank_values=True))
    normalized_query = urlencode(sorted_params)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, normalized_query, ""))


def should_continue_pagination(next_url: str | None, visited_urls: set[str]) -> bool:
    """Return False when no next URL or next URL is already visited."""
    if next_url is None:
        return False
    return normalize_page_url(next_url) not in visited_urls


def _extract_offset_from_url(url: str) -> int | None:
    parts = urlsplit(url)
    params = dict(parse_qsl(parts.query, keep_blank_values=True))

    raw_value = params.get("dispStartIndex")
    if raw_value is None:
        raw_value = params.get("idx")

    if raw_value is None:
        return None
    if not raw_value.isdigit():
        return None
    return int(raw_value)
