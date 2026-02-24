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

基本構文:

```bash
jalan-search [--help] <command> [options]
```

利用できるサブコマンド:
- `area`: 都道府県配下のSMLエリアを巡回して検索（US-01）
- `list`: `data/candidate_hotels.csv` の候補宿名で one-shot キーワード検索（US-02）

### `area` オプション

| オプション | 必須 | 既定値 | 説明 |
|---|---|---|---|
| `--checkin YYYY-MM-DD` | 必須 | - | 宿泊日 |
| `--pref <都道府県名>` | 任意 | なし | 複数指定可。`--pref 北海道 --pref 青森県` または `--pref 北海道,青森県` |
| `--adults <int>` | 任意 | `1` | 大人人数（1以上） |
| `--nights <int>` | 任意 | `1` | 泊数（1以上） |
| `--maxPrice <int>` | 任意 | 無制限 | 1人1泊あたりの予算上限（円） |
| `--meal-type <none\|breakfast\|dinner\|two_meals>` | 任意 | 指定なし | 食事条件 |
| `--care-kakenagashi / --no-care-kakenagashi` | 任意 | `--care-kakenagashi` | 温泉掛け流し条件 |
| `--care-bath-rent / --no-care-bath-rent` | 任意 | `--no-care-bath-rent` | 貸切風呂・貸切露天条件 |
| `--care-private-openair / --no-care-private-openair` | 任意 | `--no-care-private-openair` | 露天風呂付き客室条件 |
| `--parallel <int>` | 任意 | `2` | 並列数（`1..10`） |

### `list` オプション

| オプション | 必須 | 既定値 | 説明 |
|---|---|---|---|
| `--checkin YYYY-MM-DD` | 必須 | - | 入力体系統一のため必須（keyword検索URLには反映しない） |
| `--pref <都道府県名>` | 任意 | `area.xml` 上の全都道府県 | 複数指定可。keyword検索URLには反映しない |
| `--adults <int>` | 任意 | `1` | 入力受理のみ（keyword検索URLには反映しない） |
| `--nights <int>` | 任意 | `1` | 入力受理のみ（keyword検索URLには反映しない） |
| `--maxPrice <int>` | 任意 | 無制限 | 1人1泊あたりの予算上限（円）。指定時は `maxPrice` として反映 |
| `--meal-type <none\|breakfast\|dinner\|two_meals>` | 任意 | 指定なし | 入力受理のみ（keyword検索URLには反映しない） |
| `--parallel <int>` | 任意 | `2` | 並列数（`1..10`） |

補足:
- `list` は候補ファイルを `data/candidate_hotels.csv` 固定で使用します（`--names-file` は非対応）。
- `area` で `--pref` 未指定の場合、検索対象エリアが空になり結果は0件になります。

### 実行例

ヘルプ:

```bash
jalan-search --help
```

都道府県で検索:

```bash
jalan-search area \
  --checkin 2026-03-10 \
  --pref 北海道
```

複数都道府県 + 条件指定:

```bash
jalan-search area \
  --checkin 2026-03-10 \
  --pref 北海道,青森県 \
  --meal-type two_meals \
  --no-care-kakenagashi \
  --care-bath-rent \
  --parallel 4
```

候補CSVで絞り込み:

```bash
jalan-search list \
  --checkin 2026-03-10 \
  --pref 北海道
```

## Output

標準出力（`stdout`）は `text-list` 固定です。ログ/エラーは標準エラー（`stderr`）に出ます。

検索結果あり（`stdout`）:

```text
検索結果: 1件

[1] 宿名: 札幌温泉ホテル
URL: https://www.jalan.net/yad123456/
  - プラン1: 夕朝食付き / 12,000円
```

検索結果なし（`stdout`）:

```text
該当する宿はありませんでした。
```

取得失敗時の例（`stderr`）:

```text
area fetch failed: area=SML_010202 url=https://example.com reason=timeout
```

終了コード:

| 終了コード | 意味 |
|---|---|
| `0` | 正常終了 |
| `1` | 予期しない例外 |
| `2` | 入力不備 / 未対応コマンド（例: `coupon`） |
| `3` | 取得失敗（v1は stop ポリシー固定） |

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
