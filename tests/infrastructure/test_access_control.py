import asyncio

from jalan_hotel_finder.infrastructure.access_control import (
    AccessRestrictedError,
    is_access_restricted,
    is_retryable_exception,
)


def test_detects_access_restriction_for_429_and_403() -> None:
    assert is_access_restricted(429, "", hotel_link_count=1) is True
    assert is_access_restricted(403, "", hotel_link_count=10) is True


def test_detects_access_restriction_for_keyword_and_no_hotel_links() -> None:
    body = "ただいまアクセスが集中しています。しばらく時間をおいてください"

    assert is_access_restricted(200, body, hotel_link_count=0) is True
    assert is_access_restricted(200, body, hotel_link_count=1) is False


def test_timeout_is_retryable_but_restriction_is_not() -> None:
    assert is_retryable_exception(asyncio.TimeoutError()) is True
    assert is_retryable_exception(TimeoutError()) is True
    assert is_retryable_exception(AccessRestrictedError("blocked")) is False
