# jalan-hotel-finder

じゃらんnetの宿検索を効率化する個人向けCLIツールの仕様策定リポジトリです。

## Status

v1 CLI実装完了（2026-02-22）。

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
pip install -e .
python -m playwright install chromium
```

## Global CLI Install

`jalan-search` をグローバルに使う場合は、リポジトリ直下で以下を実行します。

```bash
cd /mnt/c/users/ytanaka/Documents/Jaran
python3 -m pip install --user --break-system-packages -e .
```

- 本プロジェクトはPyPI等に公開していないため、`pip install jalan-hotel-finder` のような外部取得はできません。
- `-e .` は現在のローカルリポジトリを参照するインストールです（別ディレクトリで実行しても同じ効果になりません）。
- `~/.local/bin` が `PATH` に入っていれば、どこからでも `jalan-search` を実行できます。

## CLI Usage

ヘルプ:

```bash
jalan-search --help
```

都道府県で検索（US-01）:

```bash
jalan-search area \
  --checkin 2026-03-10 \
  --pref 北海道
```

候補CSVで絞り込み（US-02）:

```bash
jalan-search list \
  --checkin 2026-03-10
```

US-02は `data/candidate_hotels.csv` を固定で使用し、`--pref` 省略時は全都道府県が使われます。

## CI

- `push`（`main`）と `pull_request` で GitHub Actions の `CI Tests` が `pytest` を実行します。
- マージ/リリース前は Actions の成功（green）を確認してください。
