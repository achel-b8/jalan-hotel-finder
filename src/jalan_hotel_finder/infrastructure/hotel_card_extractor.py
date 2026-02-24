"""Extract hotel cards from Jalan result HTML."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any
from urllib.parse import urljoin

from selectolax.parser import HTMLParser, Node


_HOTEL_URL_PATTERN = re.compile(r"/yad\d+/?")
_OPEN_YADO_SYOSAI_PATTERN = re.compile(r"openYadoSyosai\(\s*['\"](?P<yad>\d{6})['\"]")
_PRICE_PATTERN = re.compile(r"(\d[\d,]*)")


def extract_hotel_cards_from_html(html: str) -> list[dict[str, Any]]:
    """Extract hotel_name, hotel_url, plan_name, price from one page."""
    tree = HTMLParser(html)

    dom_cards = _extract_from_dom(tree)
    structured_cards = _extract_from_json_ld(tree)
    if not structured_cards:
        return dom_cards

    structured_by_path: dict[str, dict[str, Any]] = {}
    for card in structured_cards:
        path = _normalize_hotel_path(card["hotel_url"])
        structured_by_path.setdefault(path, card)

    merged: list[dict[str, Any]] = []
    seen_dom_paths: set[str] = set()

    for card in dom_cards:
        path = _normalize_hotel_path(card["hotel_url"])
        structured_fallback = structured_by_path.get(path)
        merged_card = dict(card)
        if structured_fallback is not None and merged_card["price"] is None:
            merged_card["price"] = structured_fallback["price"]
        merged.append(merged_card)
        seen_dom_paths.add(path)

    for card in structured_cards:
        path = _normalize_hotel_path(card["hotel_url"])
        if path in seen_dom_paths:
            continue
        merged.append(card)

    return merged


def _extract_from_json_ld(tree: HTMLParser) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for script in tree.css("script[type='application/ld+json']"):
        raw_json = script.text(deep=False, separator=" ").strip()
        if not raw_json:
            continue

        try:
            loaded = json.loads(raw_json)
        except json.JSONDecodeError:
            continue

        for hotel_obj in _iter_hotel_objects(loaded):
            hotel_name = hotel_obj.get("name")
            hotel_url = _normalize_hotel_url(hotel_obj.get("url"))
            if not isinstance(hotel_name, str) or not hotel_name.strip() or not hotel_url:
                continue

            cards.append(
                {
                    "hotel_name": hotel_name.strip(),
                    "hotel_url": hotel_url,
                    "plan_name": "",
                    "price": _parse_price(hotel_obj.get("priceRange")),
                }
            )

    return cards


def _iter_hotel_objects(data: Any) -> Iterable[dict[str, Any]]:
    if isinstance(data, list):
        for item in data:
            yield from _iter_hotel_objects(item)
        return

    if not isinstance(data, dict):
        return

    obj_type = data.get("@type")
    if isinstance(obj_type, str) and obj_type.lower() == "hotel":
        yield data

    graph = data.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            yield from _iter_hotel_objects(item)


def _extract_from_dom(tree: HTMLParser) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen_card_keys: set[tuple[str, str, int | None]] = set()
    seen_paths_from_modern: set[str] = set()

    for card in _extract_from_modern_dom(tree):
        normalized_path = _normalize_hotel_path(card["hotel_url"])
        card_key = (normalized_path, card["plan_name"], card["price"])
        if card_key in seen_card_keys:
            continue
        cards.append(card)
        seen_card_keys.add(card_key)
        seen_paths_from_modern.add(normalized_path)

    seen_paths_from_anchor: set[str] = set()
    for anchor in tree.css("a[href], a[data-href]"):
        if _is_noise_link(anchor):
            continue

        hotel_url = _normalize_hotel_url(_extract_link_target(anchor))
        if not hotel_url:
            continue

        normalized_path = _normalize_hotel_path(hotel_url)
        if normalized_path in seen_paths_from_modern:
            continue
        if normalized_path in seen_paths_from_anchor:
            continue

        hotel_name = _find_hotel_name(anchor)
        if not hotel_name:
            continue

        plan_name = _find_related_text(
            anchor,
            [
                ".p-searchResultItem__planName",
                ".plan-name",
                ".planName",
                "[data-testid='plan-name']",
                ".hotel-plan-name",
            ],
        )
        price_text = _find_related_text(
            anchor,
            [
                ".p-searchResultItem__perPersonPrice",
                ".p-searchResultItem__lowestPriceValue",
                ".price",
                ".plan-price",
                ".planPrice",
                "[data-testid='price']",
            ],
        )

        cards.append(
            {
                "hotel_name": hotel_name,
                "hotel_url": hotel_url,
                "plan_name": plan_name,
                "price": _parse_price(price_text),
            }
        )
        seen_paths_from_anchor.add(normalized_path)

    return cards


def _is_noise_link(anchor: Node) -> bool:
    onclick = (anchor.attributes.get("onclick") or "").lower()
    if "showyadsyoforfaq" in onclick or "showyadlistforfaq" in onclick:
        return True

    current: Node | None = anchor
    for _ in range(8):
        if current is None:
            break

        classes = (current.attributes.get("class") or "").lower()
        if "faq" in classes:
            return True

        current = current.parent

    return False


def _extract_from_modern_dom(tree: HTMLParser) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    for result_item in tree.css("li.p-yadoCassette.p-searchResultItem"):
        anchor = result_item.css_first("a.jlnpc-yadoCassette__link")
        if anchor is None:
            anchor = result_item.css_first("a[href], a[data-href]")
        if anchor is None:
            continue

        hotel_url = _normalize_hotel_url(_extract_link_target(anchor))
        if not hotel_url:
            continue

        hotel_name = _find_first_text(
            result_item,
            [".p-searchResultItem__facilityName", ".hotel-name", "h2", "h3"],
        )
        if not hotel_name:
            continue

        plan_rows = _extract_plan_rows(result_item)
        if plan_rows:
            for plan_name, plan_price in plan_rows:
                cards.append(
                    {
                        "hotel_name": hotel_name,
                        "hotel_url": hotel_url,
                        "plan_name": plan_name,
                        "price": plan_price,
                    }
                )
            continue

        cards.append(_build_fallback_card(hotel_name, hotel_url, result_item))

    return cards


def _extract_plan_rows(result_item: Node) -> list[tuple[str, int | None]]:
    plan_rows: list[tuple[str, int | None]] = []
    seen: set[tuple[str, int | None]] = set()
    for row in result_item.css("table.p-planTable tr"):
        plan_name = _find_first_text(
            row,
            [
                ".p-searchResultItem__planName",
                ".plan-name",
                ".planName",
                "[data-testid='plan-name']",
                ".hotel-plan-name",
            ],
        )
        if not plan_name:
            continue

        price_text = _find_first_text(
            row,
            [
                ".p-searchResultItem__total",
                ".p-searchResultItem__perPerson",
                ".p-searchResultItem__perPersonPrice",
                ".p-searchResultItem__lowestPriceValue",
                ".price",
                ".plan-price",
                ".planPrice",
                "[data-testid='price']",
            ],
        )
        plan_price = _parse_price(price_text)
        key = (plan_name, plan_price)
        if key in seen:
            continue

        plan_rows.append(key)
        seen.add(key)

    return plan_rows


def _build_fallback_card(hotel_name: str, hotel_url: str, result_item: Node) -> dict[str, Any]:
    plan_name = _find_first_text(
        result_item,
        [
            ".p-searchResultItem__planName",
            ".plan-name",
            ".planName",
            "[data-testid='plan-name']",
            ".hotel-plan-name",
        ],
    )
    price_text = _find_first_text(
        result_item,
        [
            ".p-searchResultItem__perPersonPrice",
            ".p-searchResultItem__lowestPriceValue",
            ".price",
            ".plan-price",
            ".planPrice",
            "[data-testid='price']",
        ],
    )

    return {
        "hotel_name": hotel_name,
        "hotel_url": hotel_url,
        "plan_name": plan_name,
        "price": _parse_price(price_text),
    }


def _find_hotel_name(anchor: Node) -> str:
    name = _find_related_text(
        anchor,
        [".p-searchResultItem__facilityName", ".hotel-name", "h2", "h3"],
        fallback_to_anchor=False,
    )
    if name:
        return name.strip()
    return anchor.text(strip=True)


def _find_first_text(node: Node, selectors: list[str]) -> str:
    for selector in selectors:
        found = node.css_first(selector)
        if found is None:
            continue
        text = found.text(strip=True)
        if text:
            return text
    return ""


def _find_related_text(
    anchor: Node,
    selectors: list[str],
    fallback_to_anchor: bool = True,
) -> str:
    current: Node | None = anchor
    for _ in range(5):
        if current is None:
            break
        for selector in selectors:
            found = current.css_first(selector)
            if found is not None:
                text = found.text(strip=True)
                if text:
                    return text
        current = current.parent

    if fallback_to_anchor:
        text = anchor.text(strip=True)
        return text or ""
    return ""


def _extract_link_target(anchor: Node) -> str:
    return (anchor.attributes.get("href") or anchor.attributes.get("data-href") or "").strip()


def _normalize_hotel_url(raw_url: Any) -> str:
    if not isinstance(raw_url, str) or not raw_url.strip():
        return ""

    normalized_raw = raw_url.strip()
    js_match = _OPEN_YADO_SYOSAI_PATTERN.search(normalized_raw)
    if js_match is not None:
        return urljoin("https://www.jalan.net", f"/yad{js_match.group('yad')}/")

    absolute_url = urljoin("https://www.jalan.net", normalized_raw)
    match = _HOTEL_URL_PATTERN.search(absolute_url)
    if match is None:
        return ""

    path = match.group(0)
    if not path.startswith("/"):
        path = f"/{path}"

    return urljoin("https://www.jalan.net", path)


def _normalize_hotel_path(url: str) -> str:
    match = _HOTEL_URL_PATTERN.search(url)
    if match is None:
        return url
    return match.group(0).rstrip("/")


def _parse_price(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if not isinstance(value, str):
        return None

    match = _PRICE_PATTERN.search(value)
    if match is None:
        return None

    return int(match.group(1).replace(",", ""))
