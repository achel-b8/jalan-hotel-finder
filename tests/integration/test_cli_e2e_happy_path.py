import importlib
import os
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from typer.testing import CliRunner

from jalan_hotel_finder.application import search_services
from jalan_hotel_finder.infrastructure.crawler import PlaywrightPageFetcher


pytestmark = [
    pytest.mark.external_e2e,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_E2E") != "1",
        reason="set RUN_LIVE_E2E=1 to run live E2E with real Playwright",
    ),
]

cli_module = importlib.import_module("jalan_hotel_finder.cli.app")
runner = CliRunner()
_EXPECTED_LIVE_NORMALIZED_URLS = {"/yad386526", "/yad377160"}


def _future_checkin(days_from_today: int = 30) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


def _resolver_single_area(prefecture_name: str) -> list[str]:
    if prefecture_name == "北海道":
        return ["SML_010202"]
    raise ValueError(f"unexpected prefecture in live E2E: {prefecture_name}")


def _force_idx_offset(url: str, idx: int = 9999) -> str:
    parts = urlsplit(url)
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    params["idx"] = str(idx)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment)
    )


def _patch_live_playwright_route(monkeypatch) -> dict[str, int]:
    fetch_count = {"value": 0}

    original_fetch = PlaywrightPageFetcher.fetch
    original_build_url = search_services.build_search_area_url

    async def _counting_fetch(self: PlaywrightPageFetcher, url: str):
        fetch_count["value"] += 1
        return await original_fetch(self, url)

    def _single_page_url(sml_code: str, user_input) -> str:  # type: ignore[no-untyped-def]
        return _force_idx_offset(original_build_url(sml_code, user_input))

    monkeypatch.setattr(PlaywrightPageFetcher, "fetch", _counting_fetch)
    monkeypatch.setattr(cli_module, "resolve_sml_codes_for_prefecture", _resolver_single_area)
    monkeypatch.setattr(search_services, "build_search_area_url", _single_page_url)
    return fetch_count


def _extract_result_count(output: str) -> int:
    matched = re.search(r"検索結果:\s*(\d+)件", output)
    if matched is None:
        return 0
    return int(matched.group(1))


def test_e2e_live_search_area_uses_real_playwright_and_returns_list(monkeypatch) -> None:
    fetch_count = _patch_live_playwright_route(monkeypatch)

    result = runner.invoke(
        cli_module.app,
        [
            "area",
            "--checkin",
            _future_checkin(),
            "--pref",
            "北海道",
            "--parallel",
            "1",
        ],
    )

    assert result.exit_code == 0, result.stderr
    assert fetch_count["value"] >= 1

    result_count = _extract_result_count(result.stdout)
    assert result_count >= 1, "live area search returned empty output"
    assert "宿名:" in result.stdout
    assert "URL: https://www.jalan.net/yad" in result.stdout


def test_e2e_live_search_names_uses_real_playwright_and_returns_list(
    monkeypatch,
    tmp_path: Path,
) -> None:
    default_names_file = tmp_path / "candidate_hotels.csv"
    default_names_file.write_text(
        "宿名,URL,優先オプション\n"
        "川島旅館,https://www.jalan.net/yad386526/?yadNo=386526,\n"
        "ピリカ,https://www.jalan.net/yad377160/?yadNo=377160,\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli_module, "DEFAULT_NAMES_FILE", default_names_file)
    fetch_count = _patch_live_playwright_route(monkeypatch)

    result = runner.invoke(
        cli_module.app,
        [
            "list",
            "--checkin",
            _future_checkin(),
            "--pref",
            "北海道",
            "--parallel",
            "1",
        ],
    )

    assert result.exit_code == 0, result.stderr
    assert fetch_count["value"] >= 1

    result_count = _extract_result_count(result.stdout)
    assert result_count >= 1, "live names search returned empty output"
    assert "宿名:" in result.stdout
    assert any(
        f"https://www.jalan.net{normalized_url}/" in result.stdout
        for normalized_url in _EXPECTED_LIVE_NORMALIZED_URLS
    )


def test_e2e_live_search_names_with_default_pref_uses_real_playwright(
    monkeypatch,
    tmp_path: Path,
) -> None:
    default_names_file = tmp_path / "candidate_hotels.csv"
    default_names_file.write_text(
        "宿名,URL,優先オプション\n"
        "川島旅館,https://www.jalan.net/yad386526/?yadNo=386526,\n"
        "ピリカ,https://www.jalan.net/yad377160/?yadNo=377160,\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli_module, "DEFAULT_NAMES_FILE", default_names_file)
    monkeypatch.setattr(cli_module, "list_prefecture_names", lambda: ["北海道"])
    fetch_count = _patch_live_playwright_route(monkeypatch)

    result = runner.invoke(
        cli_module.app,
        [
            "list",
            "--checkin",
            _future_checkin(),
            "--parallel",
            "1",
        ],
    )

    assert result.exit_code == 0, result.stderr
    assert fetch_count["value"] >= 1

    result_count = _extract_result_count(result.stdout)
    assert result_count >= 1, "live names search with default pref returned empty output"
    assert any(
        f"https://www.jalan.net{normalized_url}/" in result.stdout
        for normalized_url in _EXPECTED_LIVE_NORMALIZED_URLS
    )
