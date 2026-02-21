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

### 1. Pythonコマンド有効化（WSL/Ubuntu）

`python` コマンドが存在しない環境では先に以下を実行してください。

```bash
sudo apt update
sudo apt install -y python-is-python3 python3-venv
```

### 2. Python依存関係

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

### 3. Playwright (Chromium) + OS依存ライブラリ

Linux/WSL2 では、Playwrightブラウザ本体に加えてOS側ライブラリが必要です。

```bash
python -m playwright install --with-deps chromium
```

- `--with-deps` は Debian/Ubuntu 系で必要な共有ライブラリも一緒に入れます（`sudo` 権限が必要）。
- 典型例: `libnspr4.so` / `libnss3.so` が見つからないエラー。

不足ライブラリだけ先に補う場合:

```bash
sudo apt update
sudo apt install -y libnspr4 libnss3
```

### 4. 起動確認（任意）

`pytest` が通っても実行時のブラウザ起動で失敗するケースを切り分けるため、以下で最低限の起動確認ができます。

```bash
python - <<'PY'
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        await browser.close()

asyncio.run(main())
print("playwright launch OK")
PY
```

## Global CLI Install

`jalan-search` をグローバルに使う場合は、リポジトリ直下で以下を実行します。

```bash
cd /mnt/c/users/ytanaka/Documents/Jaran
python -m pip install --user --break-system-packages -e .
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

US-02は `data/candidate_hotels.csv` を固定で使用し、候補宿名ごとにキーワード検索URLを1回だけ取得して照合します（ページ送りなし）。

## Test Execution

通常テスト（ライブE2Eはスキップ）:

```bash
python -m pytest
```

コミット/プッシュ前の最終確認（ライブE2E込み）:

```bash
RUN_LIVE_E2E=1 python -m pytest
```

- `tests/integration/test_cli_e2e_happy_path.py` は実Playwrightで `https://www.jalan.net` に接続します。
- 通常実行では `RUN_LIVE_E2E=1` を付けない限りスキップされます。

## CI

- `push`（`main`）と `pull_request` で GitHub Actions の `CI Tests` が `pytest` を実行します。
- CIでは `RUN_LIVE_E2E=1` を有効化し、ライブE2Eも含めて実行します。
- マージ/リリース前は Actions の成功（green）を確認してください。
