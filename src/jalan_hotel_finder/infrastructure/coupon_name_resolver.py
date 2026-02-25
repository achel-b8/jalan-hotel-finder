"""Resolve coupon IDs from Jalan coupon source pages."""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen

from selectolax.parser import HTMLParser


class CouponSourceFetchError(RuntimeError):
    """Raised when coupon source data cannot be fetched."""


class CouponNameNotFoundError(ValueError):
    """Raised when no coupon ID matches the input name."""


class CouponNameAmbiguousError(ValueError):
    """Raised when multiple coupon IDs match the same name."""


CouponCandidate = tuple[str, str]


def resolve_coupon_id(
    coupon_name: str,
    coupon_source_url: str,
    *,
    fetch_text: Callable[[str], str] | None = None,
) -> str:
    """Resolve one coupon ID from source URL and coupon display name."""
    normalized_name = coupon_name.strip()
    if not normalized_name:
        raise ValueError("coupon_name must not be empty")

    normalized_source_url = coupon_source_url.strip()
    if not normalized_source_url:
        raise ValueError("coupon_source_url must not be empty")

    text_fetcher = fetch_text or _fetch_text
    if _is_kikaku_source(normalized_source_url):
        area_json_url = _build_kikaku_area_json_url(normalized_source_url)
        raw_json = text_fetcher(area_json_url)
        candidates = _load_candidates_from_kikaku_json(raw_json)
    else:
        html = text_fetcher(normalized_source_url)
        candidates = _load_candidates_from_coupon_page_html(html)

    matched_ids = sorted(
        {
            coupon_id
            for candidate_name, coupon_id in candidates
            if candidate_name == normalized_name and coupon_id
        }
    )
    if not matched_ids:
        raise CouponNameNotFoundError(f"coupon name not found: {normalized_name}")
    if len(matched_ids) > 1:
        joined = ", ".join(matched_ids)
        raise CouponNameAmbiguousError(
            f"coupon name is ambiguous: {normalized_name} ({joined})"
        )
    return matched_ids[0]


def _is_kikaku_source(source_url: str) -> bool:
    parsed = urlsplit(source_url)
    normalized_path = parsed.path.rstrip("/")
    return normalized_path.endswith("/theme/coupon/kikaku")


def _build_kikaku_area_json_url(source_url: str) -> str:
    parsed = urlsplit(source_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"invalid coupon source URL: {source_url}")
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            "/theme/coupon/kikaku/json/area.json",
            "",
            "",
        )
    )


def _load_candidates_from_kikaku_json(raw_json: str) -> list[CouponCandidate]:
    try:
        loaded = json.loads(raw_json)
    except json.JSONDecodeError as error:
        raise CouponSourceFetchError("failed to parse kikaku area.json") from error

    coupon_list = loaded.get("couponKenlrgList")
    if not isinstance(coupon_list, list):
        return []

    candidates: list[CouponCandidate] = []
    for item in coupon_list:
        if not isinstance(item, dict):
            continue
        coupon_name = item.get("couponName")
        coupon_id = item.get("couponID")
        if not isinstance(coupon_name, str) or not isinstance(coupon_id, str):
            continue
        normalized_name = coupon_name.strip()
        normalized_id = coupon_id.strip()
        if not normalized_name or not normalized_id:
            continue
        candidates.append((normalized_name, normalized_id))
    return candidates


def _load_candidates_from_coupon_page_html(html: str) -> list[CouponCandidate]:
    tree = HTMLParser(html)
    candidates: list[CouponCandidate] = []
    seen: set[CouponCandidate] = set()

    selectors = [
        "select#coupon_list option",
        "select[name='couponId'] option",
        "select[name='defaultCouponId'] option",
    ]
    for selector in selectors:
        for option in tree.css(selector):
            coupon_id = (option.attributes.get("value") or "").strip()
            coupon_name = option.text(strip=True)
            if not coupon_id or not coupon_name:
                continue
            candidate = (coupon_name, coupon_id)
            if candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)

    return candidates


def _fetch_text(url: str) -> str:
    try:
        with urlopen(url, timeout=30) as response:
            body = response.read()
            encoding = response.headers.get_content_charset()
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        raise CouponSourceFetchError(f"failed to fetch coupon source URL: {url}") from error

    if encoding:
        try:
            return body.decode(encoding)
        except LookupError:
            pass
        except UnicodeDecodeError:
            pass

    for fallback in ("cp932", "utf-8", "shift_jis"):
        try:
            return body.decode(fallback)
        except UnicodeDecodeError:
            continue

    return body.decode("utf-8", errors="ignore")
