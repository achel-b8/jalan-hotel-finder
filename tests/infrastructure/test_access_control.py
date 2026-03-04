import asyncio

from jalan_hotel_finder.infrastructure.access_control import (
    AccessRestrictedError,
    InvalidAreaRouteError,
    is_invalid_area_route_suspected,
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


def test_detects_invalid_area_route_for_error_template_on_sml_path() -> None:
    body = (
        "<title>エラー画面</title>"
        "ただ今の時間帯アクセスが集中しているため、つながりにくくなっております。"
    )

    assert (
        is_invalid_area_route_suspected(
            url="https://www.jalan.net/100000/LRG_101400/SML_101402/",
            status_code=200,
            body_text=body,
            hotel_link_count=0,
        )
        is True
    )
    assert (
        is_invalid_area_route_suspected(
            url="https://www.jalan.net/uw/uwp2011/uww2011init.do?keyword=%8eB",
            status_code=200,
            body_text=body,
            hotel_link_count=0,
        )
        is False
    )


def test_timeout_is_retryable_but_restriction_is_not() -> None:
    assert is_retryable_exception(asyncio.TimeoutError()) is True
    assert is_retryable_exception(TimeoutError()) is True
    assert is_retryable_exception(AccessRestrictedError("blocked")) is False
    assert is_retryable_exception(InvalidAreaRouteError("invalid route")) is False
