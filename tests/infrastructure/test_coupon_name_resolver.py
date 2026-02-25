from pathlib import Path

import pytest

from jalan_hotel_finder.infrastructure.coupon_name_resolver import (
    CouponNameAmbiguousError,
    CouponNameNotFoundError,
    CouponSourceFetchError,
    resolve_coupon_id,
)


def _read_fixture(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_resolves_coupon_id_from_discount_coupon_page_html() -> None:
    html = _read_fixture("tests/fixtures/html/coupon_source_discount_sample.html")

    actual = resolve_coupon_id(
        coupon_name="【全国(対象施設のみ)】9,000円お得クーポン",
        coupon_source_url="https://www.jalan.net/discountCoupon/CAM1598252/",
        fetch_text=lambda _: html,
    )

    assert actual == "COU1111111"


def test_resolves_coupon_id_from_kikaku_area_json() -> None:
    area_json = _read_fixture("tests/fixtures/json/coupon_kikaku_area_sample.json")
    source_url = "https://www.jalan.net/theme/coupon/kikaku/"
    expected_area_json_url = "https://www.jalan.net/theme/coupon/kikaku/json/area.json"

    def _fetch_text(url: str) -> str:
        if url == expected_area_json_url:
            return area_json
        raise AssertionError(f"unexpected url: {url}")

    actual = resolve_coupon_id(
        coupon_name="2月【じゃらんのお得な10日間】50000円から使える5000円クーポン",
        coupon_source_url=source_url,
        fetch_text=_fetch_text,
    )

    assert actual == "COU4444444"


def test_resolves_coupon_id_from_kikaku_source_without_trailing_slash() -> None:
    area_json = _read_fixture("tests/fixtures/json/coupon_kikaku_area_sample.json")
    source_url = "https://www.jalan.net/theme/coupon/kikaku"
    expected_area_json_url = "https://www.jalan.net/theme/coupon/kikaku/json/area.json"

    def _fetch_text(url: str) -> str:
        if url == expected_area_json_url:
            return area_json
        raise AssertionError(f"unexpected url: {url}")

    actual = resolve_coupon_id(
        coupon_name="2月【じゃらんのお得な10日間】50000円から使える5000円クーポン",
        coupon_source_url=source_url,
        fetch_text=_fetch_text,
    )

    assert actual == "COU4444444"


def test_raises_when_coupon_name_is_not_found() -> None:
    html = _read_fixture("tests/fixtures/html/coupon_source_discount_sample.html")

    with pytest.raises(CouponNameNotFoundError):
        resolve_coupon_id(
            coupon_name="存在しないクーポン名",
            coupon_source_url="https://www.jalan.net/discountCoupon/CAM1598252/",
            fetch_text=lambda _: html,
        )


def test_raises_when_coupon_name_is_ambiguous() -> None:
    ambiguous_html = """
    <html><body>
      <select id="coupon_list">
        <option value="COU1111111">同名クーポン</option>
        <option value="COU2222222">同名クーポン</option>
      </select>
    </body></html>
    """

    with pytest.raises(CouponNameAmbiguousError):
        resolve_coupon_id(
            coupon_name="同名クーポン",
            coupon_source_url="https://www.jalan.net/discountCoupon/CAM0000000/",
            fetch_text=lambda _: ambiguous_html,
        )


def test_raises_when_kikaku_area_json_is_invalid() -> None:
    with pytest.raises(CouponSourceFetchError):
        resolve_coupon_id(
            coupon_name="any",
            coupon_source_url="https://www.jalan.net/theme/coupon/kikaku/",
            fetch_text=lambda _: "{not-json}",
        )
