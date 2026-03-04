"""Access restriction detection and retry classification."""

from __future__ import annotations

import asyncio
import re
from urllib.parse import urlsplit


RESTRICTION_KEYWORDS_V1 = (
    "アクセスが集中",
    "ただいまアクセスが集中",
    "ご利用を制限",
    "しばらく時間をおいて",
    "短時間に多くのアクセス",
    "不正なアクセス",
    "Too Many Requests",
    "Forbidden",
)


class AccessRestrictedError(RuntimeError):
    """Raised when Jalan appears to apply access restrictions."""


class InvalidAreaRouteError(RuntimeError):
    """Raised when an area route looks invalid and returns Jalan error template."""


_AREA_ROUTE_PATH_PATTERN = re.compile(r"^/\d{6}/LRG_\d{6}/SML_\d{6}/$")
_INVALID_ROUTE_TEMPLATE_KEYWORDS_V1 = (
    "エラー画面",
    "ただ今の時間帯アクセスが集中しているため",
)


def is_access_restricted(
    status_code: int | None,
    body_text: str,
    hotel_link_count: int,
) -> bool:
    """Check status/text signals and decide whether to stop immediately."""
    if status_code in {403, 429}:
        return True

    if any(keyword in body_text for keyword in RESTRICTION_KEYWORDS_V1):
        return hotel_link_count == 0

    return False


def is_invalid_area_route_suspected(
    url: str,
    status_code: int | None,
    body_text: str,
    hotel_link_count: int,
) -> bool:
    """Detect likely invalid area routes from Jalan's generic error template."""
    if status_code != 200:
        return False
    if hotel_link_count != 0:
        return False

    path = urlsplit(url).path
    if _AREA_ROUTE_PATH_PATTERN.fullmatch(path) is None:
        return False

    return all(keyword in body_text for keyword in _INVALID_ROUTE_TEMPLATE_KEYWORDS_V1)


def raise_if_invalid_area_route_suspected(
    url: str,
    status_code: int | None,
    body_text: str,
    hotel_link_count: int,
) -> None:
    """Raise InvalidAreaRouteError when area route response matches invalid template."""
    if is_invalid_area_route_suspected(url, status_code, body_text, hotel_link_count):
        raise InvalidAreaRouteError(
            f"invalid area route suspected (status={status_code}, hotel_links={hotel_link_count})"
        )


def raise_if_access_restricted(
    status_code: int | None,
    body_text: str,
    hotel_link_count: int,
) -> None:
    """Raise AccessRestrictedError if response matches restriction signals."""
    if is_access_restricted(status_code, body_text, hotel_link_count):
        raise AccessRestrictedError(
            f"access restriction detected (status={status_code}, hotel_links={hotel_link_count})"
        )


def is_retryable_exception(error: Exception) -> bool:
    """Return True only for temporary failures expected to recover by retry."""
    if isinstance(error, (AccessRestrictedError, InvalidAreaRouteError)):
        return False

    if isinstance(error, (TimeoutError, asyncio.TimeoutError, OSError)):
        return True

    return False


def is_retryable_status(status_code: int | None) -> bool:
    """4xx are non-retryable in v1 except restriction handling with immediate stop."""
    if status_code is None:
        return False
    if status_code in {403, 429}:
        return False
    return 500 <= status_code <= 599
