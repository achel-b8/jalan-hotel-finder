# jalan-hotel-finder

じゃらんnetの宿検索を効率化する個人向けCLIツールの仕様策定リポジトリです。

## Status

仕様策定完了（2026-02-21）。

## Spec Documents

- `docs/CLI仕様書.md`: v1 CLI仕様（ユーザーストーリー/受け入れ要件）
- `docs/じゃらん仕様調査.md`: じゃらん仕様調査
- `docs/技術アーキテクチャ設計書.md`: 技術選定と実装アーキテクチャ設計

## Dependency Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m playwright install chromium
```

## CI

- `push`（`main`）と `pull_request` で GitHub Actions の `CI Tests` が `pytest` を実行します。
- マージ/リリース前は Actions の成功（green）を確認してください。
