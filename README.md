# jalan-hotel-finder

じゃらんnetの宿検索を効率化する個人向けCLIツールの仕様策定リポジトリです。

## Status

仕様策定完了（2026-02-21）。

## Spec Documents

- `docs/CLI仕様書.md`: v1 CLI仕様（ユーザーストーリー/受け入れ要件）
- `docs/じゃらん仕様調査.md`: じゃらん仕様調査
- `docs/技術アーキテクチャ設計書.md`: 技術選定と実装アーキテクチャ設計

## Candidate File (US-02)

- 実データの候補宿CSVは `data/candidate_hotels.csv` に配置しています。
- 列は `宿名,URL,優先オプション` の3項目です（`優先オプション` は任意・複数指定可）。

## Dependency Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m playwright install chromium
```

## CLI Usage

ヘルプ:

```bash
PYTHONPATH=src .venv/bin/python -m typer jalan_hotel_finder.cli.app run --help
```

都道府県で検索（US-01）:

```bash
PYTHONPATH=src .venv/bin/python -m typer jalan_hotel_finder.cli.app run search area \
  --checkin 2026-03-10 \
  --pref 北海道
```

候補CSVで絞り込み（US-02）:

```bash
PYTHONPATH=src .venv/bin/python -m typer jalan_hotel_finder.cli.app run search names \
  --checkin 2026-03-10
```

`--names-file` は省略時に `data/candidate_hotels.csv`、`--pref` は省略時に全都道府県が使われます。

## CI

- `push`（`main`）と `pull_request` で GitHub Actions の `CI Tests` が `pytest` を実行します。
- マージ/リリース前は Actions の成功（green）を確認してください。
