import importlib
import json
from pathlib import Path

from typer.testing import CliRunner

from jalan_hotel_finder.application.input_models import SearchAreaInput
from jalan_hotel_finder.application.query_builder import build_search_area_url
from jalan_hotel_finder.infrastructure.crawler import FetchResult


cli_module = importlib.import_module("jalan_hotel_finder.cli.app")
runner = CliRunner()


def _fixture(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _resolver(prefecture_name: str) -> list[str]:
    if prefecture_name == "北海道":
        return ["SML_010202"]
    raise ValueError(f"unknown prefecture: {prefecture_name}")


def _make_fake_playwright_fetcher(html_by_url: dict[str, str]):
    class _FakePlaywrightPageFetcher:
        def __init__(self, page_load_timeout_ms: int = 30_000, headless: bool = True) -> None:
            self._page_load_timeout_ms = page_load_timeout_ms
            self._headless = headless

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def fetch(self, url: str) -> FetchResult:
            html = html_by_url.get(url)
            if html is None:
                raise AssertionError(f"unexpected url: {url}")
            return FetchResult(url=url, html=html, status_code=200)

    return _FakePlaywrightPageFetcher


def test_e2e_happy_path_search_area_returns_exit_code_0_and_expected_json(monkeypatch) -> None:
    user_input = SearchAreaInput(checkin="2026-03-10", pref=["北海道"])
    first_url = build_search_area_url("SML_010202", user_input)
    second_url = "https://www.jalan.net/010000/LRG_010200/SML_010202/?idx=30"

    monkeypatch.setattr(cli_module, "resolve_sml_codes_for_prefecture", _resolver)
    monkeypatch.setattr(
        cli_module,
        "PlaywrightPageFetcher",
        _make_fake_playwright_fetcher(
            {
                first_url: _fixture("tests/fixtures/html/integration/area_page1.html"),
                second_url: _fixture("tests/fixtures/html/integration/area_page2.html"),
            }
        ),
    )

    result = runner.invoke(
        cli_module.app,
        [
            "search",
            "area",
            "--checkin",
            "2026-03-10",
            "--pref",
            "北海道",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 2
    assert payload[0]["hotel_name"] == "札幌温泉ホテル"
    assert payload[1]["hotel_name"] == "函館シティホテル"


def test_e2e_happy_path_search_names_returns_exit_code_0_and_filtered_json(
    monkeypatch,
    tmp_path: Path,
) -> None:
    names_file = tmp_path / "names.txt"
    names_file.write_text("札幌\n", encoding="utf-8")

    user_input = SearchAreaInput(checkin="2026-03-10", pref=["北海道"])
    first_url = build_search_area_url("SML_010202", user_input)

    monkeypatch.setattr(cli_module, "resolve_sml_codes_for_prefecture", _resolver)
    monkeypatch.setattr(
        cli_module,
        "PlaywrightPageFetcher",
        _make_fake_playwright_fetcher(
            {
                first_url: _fixture("tests/fixtures/html/integration/names_page.html"),
            }
        ),
    )

    result = runner.invoke(
        cli_module.app,
        [
            "search",
            "names",
            "--names-file",
            str(names_file),
            "--checkin",
            "2026-03-10",
            "--pref",
            "北海道",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 1
    assert payload[0]["search_type"] == "name"
    assert payload[0]["matched_name"] == "札幌"
    assert payload[0]["hotel_name"] == "札幌温泉ホテル"
