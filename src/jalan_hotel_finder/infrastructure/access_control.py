"""Access restriction detection and retry classification."""

from __future__ import annotations

import asyncio


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
    if isinstance(error, AccessRestrictedError):
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
