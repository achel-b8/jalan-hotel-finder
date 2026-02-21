import json
import importlib

from typer.testing import CliRunner

from jalan_hotel_finder.application.search_services import AreaSearchFailedError
cli_module = importlib.import_module("jalan_hotel_finder.cli.app")


runner = CliRunner()
app = cli_module.app


def test_cli_search_area_success_exit_code_0(monkeypatch) -> None:
    async def _stub_run_search_area_service(user_input):
        return [
            {
                "hotel_name": "札幌温泉ホテル",
                "hotel_url": "https://www.jalan.net/yad123456/",
                "hotel_url_normalized": "/yad123456",
                "plan_name": "夕朝食付き",
                "price": 12000,
                "search_type": "area",
                "area": "SML_010202",
            }
        ]

    monkeypatch.setattr(cli_module, "run_search_area_service", _stub_run_search_area_service)

    result = runner.invoke(
        app,
        [
            "area",
            "--checkin",
            "2026-03-10",
            "--pref",
            "北海道",
        ],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed[0]["search_type"] == "area"


def test_cli_search_names_success_exit_code_0(monkeypatch, tmp_path) -> None:
    names_file = tmp_path / "names.txt"
    names_file.write_text("札幌\n", encoding="utf-8")

    async def _stub_run_search_names_service(user_input):
        return [
            {
                "hotel_name": "札幌温泉ホテル",
                "hotel_url": "https://www.jalan.net/yad123456/",
                "hotel_url_normalized": "/yad123456",
                "plan_name": "夕朝食付き",
                "price": 12000,
                "search_type": "name",
                "area": "SML_010202",
                "matched_name": "札幌",
            }
        ]

    monkeypatch.setattr(cli_module, "run_search_names_service", _stub_run_search_names_service)
    monkeypatch.setattr(cli_module, "DEFAULT_NAMES_FILE", names_file)

    result = runner.invoke(
        app,
        [
            "list",
            "--checkin",
            "2026-03-10",
            "--pref",
            "北海道",
        ],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed[0]["search_type"] == "name"
    assert parsed[0]["matched_name"] == "札幌"


def test_cli_search_names_uses_defaults_for_names_file_and_pref(monkeypatch) -> None:
    captured = {}

    async def _stub_run_search_names_service(user_input):
        captured["names_file"] = str(user_input.names_file)
        captured["pref"] = user_input.pref
        return []

    monkeypatch.setattr(cli_module, "run_search_names_service", _stub_run_search_names_service)
    monkeypatch.setattr(cli_module, "list_prefecture_names", lambda: ["北海道", "青森県"])

    result = runner.invoke(
        app,
        [
            "list",
            "--checkin",
            "2026-03-10",
        ],
    )

    assert result.exit_code == 0
    assert captured["names_file"].endswith("data/candidate_hotels.csv")
    assert captured["pref"] == ["北海道", "青森県"]


def test_cli_list_rejects_names_file_option() -> None:
    result = runner.invoke(
        app,
        [
            "list",
            "--checkin",
            "2026-03-10",
            "--names-file",
            "data/candidate_hotels.csv",
        ],
    )

    assert result.exit_code == 2
    assert "No such option" in result.stderr


def test_cli_returns_exit_code_2_for_input_validation_error() -> None:
    result = runner.invoke(
        app,
        [
            "area",
            "--checkin",
            "2026-03-10",
            "--pref",
            "北海道",
            "--parallel",
            "11",
        ],
    )

    assert result.exit_code == 2


def test_cli_returns_exit_code_3_for_fetch_failure(monkeypatch) -> None:
    async def _stub_run_search_area_service(user_input):
        raise AreaSearchFailedError("SML_010202", "https://example.com", "timeout")

    monkeypatch.setattr(cli_module, "run_search_area_service", _stub_run_search_area_service)

    result = runner.invoke(
        app,
        [
            "area",
            "--checkin",
            "2026-03-10",
            "--pref",
            "北海道",
        ],
    )

    assert result.exit_code == 3


def test_cli_coupon_command_returns_exit_code_2() -> None:
    result = runner.invoke(app, ["coupon"])

    assert result.exit_code == 2
    assert "not supported" in result.stderr
