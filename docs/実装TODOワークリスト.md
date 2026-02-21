# jalan-hotel-finder 実装TODOワークリスト（v1）

更新日: 2026-02-21  
参照仕様:
- `docs/CLI仕様書.md`
- `docs/技術アーキテクチャ設計書.md`
- `docs/じゃらん仕様調査.md`
- `AGENTS.md`（方針・共通ルールの一次情報）

## この文書の役割
- 実装順序と依存関係を管理するタスク台帳として扱う。
- 方針・共通ルール・完了判定は `AGENTS.md` を一次情報とし、この文書には重複記載しない。

## この文書固有の運用
- 各タスクは `目的 / 成果物 / 依存タスク / テスト / 完了条件` の粒度で維持する。
- タスク状態は `[ ]` / `[x]` で管理し、完了時に更新する。
- 依存タスクが未完了の項目は着手しない。

---

## TODO一覧（依存が少ない順）

### [x] T00: プロジェクト骨組みとテスト実行基盤
- 目的: 実装を分割できる最小構成を作る。
- 成果物:
  - `src/` 配下の基本パッケージ（`cli`, `application`, `domain`, `infrastructure`, `output`）
  - `tests/` 配下の基本構成
  - `pytest` 実行設定（`pyproject.toml` or `pytest.ini`）
- 依存タスク: なし
- 前提条件: `requirements*.txt` 導入済み
- テスト:
  - import smoke test（主要モジュールが import 可能）
  - `pytest` が 0 failed で完走
- 完了条件: ローカルで `pytest` が安定実行できる。

### [x] T01: URL正規化と重複排除（純粋関数）
- 目的: 仕様の重複排除ルール（URLパス単位）を先に固定する。
- 成果物:
  - `hotel_url_normalized` 生成関数
  - 先勝ちの重複排除関数
- 依存タスク: T00
- 前提条件: なし
- テスト:
  - クエリ差分の同一URL統合
  - 末尾スラッシュ有無の扱い
  - 重複時に最初のレコードを保持
- 完了条件: `CLI仕様書 7.3` を満たす。

### [x] T02: CLI入力モデルとバリデーション
- 目的: 入力不備を早期に弾き、終了コード2に接続しやすくする。
- 成果物:
  - `area` / `list` の入力モデル
  - `parallel=1..10`、日付形式、enum制約、必須関係の検証
- 依存タスク: T00
- 前提条件: なし
- テスト:
  - 正常入力の受理
  - 範囲外 `--parallel` の拒否
  - 必須不足時の検証エラー
- 完了条件: `CLI仕様書 5.1/6.2/6.3` の入力制約を満たす。

### [x] T03: クエリビルダ（エリア検索URL生成）
- 目的: CLI入力からじゃらんパラメータへの変換を固定する。
- 成果物:
  - `SML_xxxxxx` と検索条件からURLを生成する関数
  - meal type / care系パラメータのマッピング
- 依存タスク: T02
- 前提条件: なし
- テスト:
  - `--checkin` → `stayYear/month/day`
  - meal type enum の変換
  - 固定値（`roomCount=1`, `dateUndecided=0`, `careBath=0`）の付与
- 完了条件: `CLI仕様書 6.5` の対応表どおりに出力される。

### [x] T04: area.xml リゾルバ（都道府県→SML展開）
- 目的: 都道府県指定時の検索対象展開を独立実装する。
- 成果物:
  - `area.xml` 解析ロジック
  - 都道府県名からSMLコード配列を返す関数
- 依存タスク: T00
- 前提条件: 同梱 `area.xml` スナップショットを参照できること（テストはローカルfixture可）
- テスト:
  - 代表都道府県のSML展開
  - 未知都道府県のエラー
  - 重複なし・空なしの結果保証
- 完了条件: `CLI仕様書 5.1(1)` を満たす。

### [x] T05: 宿名リスト読込とローカル照合
- 目的: `list` の核となるローカルフィルタを先に実装する。
- 成果物:
  - 候補ファイル読込関数（1行1宿名）
  - 宿名部分一致フィルタ（`matched_name` 付与）
- 依存タスク: T00, T01
- 前提条件: 文字コードは初期実装ではUTF-8想定（必要なら後続で拡張）
- テスト:
  - 1行1宿名の読込
  - 部分一致・非一致
  - 0件時に空配列を返す
- 完了条件: `CLI仕様書 5.2` を満たす。

### [x] T06: 宿カード抽出器（構造化データ優先 + フォールバック）
- 目的: HTMLから必要項目を安定抽出する。
- 成果物:
  - `hotel_name`, `hotel_url`, `plan_name`, `price` 抽出関数
  - 抽出失敗時のフォールバックセレクタ
- 依存タスク: T00
- 前提条件: サンプルHTML fixtureを準備
- テスト:
  - 正常HTMLから4項目抽出
  - 価格欠損時 `null` 扱い
  - 一部DOM欠損でも落ちない
- 完了条件: `CLI仕様書 5.1(3)` を満たす。

### [x] T07: ページネーション追跡ロジック（純粋関数）
- 目的: `idx=0,30,60...` の巡回と停止条件を固定する。
- 成果物:
  - 次ページURL生成/判定関数
  - 循環検知ロジック
- 依存タスク: T03
- 前提条件: なし
- テスト:
  - 30件刻みの次ページ遷移
  - 最終ページ停止
  - 同一URL再出現時に停止
- 完了条件: `CLI仕様書 5.1(2), 8(4)` を満たす。

### [x] T08: アクセス制限判定とリトライ判定
- 目的: 停止ポリシー `stop` に直結する判定を独立させる。
- 成果物:
  - `429/403` と本文キーワードに基づく `AccessRestrictedError`
  - リトライ対象/非対象の分類関数
- 依存タスク: T00
- 前提条件: なし
- テスト:
  - `429/403` の即時制限判定
  - キーワード + 宿リンク0件で制限判定
  - 通常タイムアウトはリトライ対象
- 完了条件: `技術アーキテクチャ設計書 4.4` を満たす。

### [x] T09: Crawler基盤（Playwright + 並列制御）
- 目的: 実ページ取得の最小実装を行う。
- 成果物:
  - Playwrightセッション管理
  - セマフォ並列（1〜10）とエリア間待機
  - ページ取得インターフェース
- 依存タスク: T02, T07, T08
- 前提条件: `python -m playwright install chromium` 済み
- テスト:
  - モックで並列上限制御を確認
  - タイムアウト時の例外変換
  - 制限判定時に即停止フローへ入る
- 完了条件: `CLI仕様書 3, 5.1(5)(6), 6.4` を満たす。

### [x] T10: `search area` アプリケーションサービス
- 目的: URL生成〜取得〜抽出〜重複排除を1ユースケースとして接続する。
- 成果物:
  - `search_area()` ユースケース
  - エリア単位失敗時の停止制御
- 依存タスク: T01, T03, T04, T06, T09
- 前提条件: なし
- テスト:
  - 複数SML統合時の重複排除
  - 1エリア失敗で終了コード3相当の例外
  - 取得0件でも正常完了
- 完了条件: `CLI仕様書 5.1` をユースケース単体で満たす。

### [x] T11: `search names` アプリケーションサービス
- 目的: `area` 結果に宿名照合を適用する。
- 成果物:
  - `search_names_local_filter()` ユースケース
  - `matched_name` 付与
- 依存タスク: T05, T10
- 前提条件: 初期は `local-filter` 固定
- テスト:
  - 部分一致結果のみ残る
  - 0件時も正常終了
  - 照合後も重複排除維持
- 完了条件: `CLI仕様書 5.2` を満たす。

### [x] T12: JSON出力整形（stdout固定）
- 目的: 出力仕様をCLIから分離して固定する。
- 成果物:
  - レコード列→JSON文字列のシリアライザ
  - `search_type`, `area`, `matched_name` の出力整合
- 依存タスク: T10, T11
- 前提条件: なし
- テスト:
  - `search area` 形式
  - `list` 形式
  - 空配列出力
- 完了条件: `CLI仕様書 7.1/7.2` を満たす。

### [x] T13: Typer CLI実装（`area` / `list`）
- 目的: ユースケースをCLIコマンドとして公開する。
- 成果物:
  - `jalan-search area`
  - `jalan-search list`
  - 未対応機能（coupon相当）時のエラーメッセージ
- 依存タスク: T02, T10, T11, T12
- 前提条件: なし
- テスト:
  - `CliRunner` で成功系（終了コード0）
  - 入力不備（終了コード2）
  - 取得失敗（終了コード3）
  - 未対応機能呼び出し（終了コード2）
- 完了条件: `CLI仕様書 6, 9` を満たす。

### [x] T14: 結合テストと最終受け入れ確認
- 目的: 受け入れ要件をテストケースへトレースし、抜け漏れをなくす。
- 成果物:
  - 受け入れ要件トレース表（要件ID ↔ テストID）
  - 最低1本の結合テスト（モック主体）
- 依存タスク: T13
- 前提条件: なし
- テスト:
  - US-01/US-02 の代表シナリオ
  - 終了コードポリシー
  - JSON出力のスナップショット
- 完了条件: `CLI仕様書 5` の全項目に対応テストが存在する。

---

## 依存関係サマリ（簡易）
- 先行推奨: `T00 → T01 → (T02, T04, T05, T06, T08) → T03 → T07 → T09 → T10 → T11 → T12 → T13 → T14`
- 最小縦スライス（最初の実装候補）: `T00 → T01 → T02 → T03 → T04 → T06 → T07 → T08 → T09 → T10`

## 着手順の提案（最初の3タスク）
1. T00（土台）
2. T01（重複排除ルール固定）
3. T02（入力制約固定）

この3つを先に完了させると、後続タスクの差分レビューが容易になる。

---

## 受け入れ要件トレース表（要件ID ↔ テストID）

| 要件ID | テストID（主要） |
|---|---|
| US-01-1 `pref -> SML展開` | `tests/infrastructure/test_area_xml_resolver.py::test_resolves_sml_codes_for_representative_prefecture` |
| US-01-2 `ページネーション追跡` | `tests/application/test_pagination.py::test_build_next_page_url_increments_by_30` / `tests/integration/test_end_to_end_mocked.py::test_integration_us01_area_search_json_snapshot` |
| US-01-3 `hotel_name/url/plan/price出力` | `tests/infrastructure/test_hotel_card_extractor.py::test_extracts_required_fields_from_normal_html` |
| US-01-4 `URLパス単位の重複排除` | `tests/domain/test_hotel_deduplication.py::test_deduplication_merges_records_when_query_is_different` / `tests/application/test_search_services.py::test_search_area_deduplicates_across_multiple_sml` |
| US-01-5 `parallel=1..10` | `tests/application/test_input_models.py::test_rejects_parallel_over_limit_for_search_area` / `tests/infrastructure/test_crawler.py::test_parallel_limit_is_respected_with_semaphore` |
| US-01-6 `1エリア失敗で停止(終了コード3)` | `tests/application/test_search_services.py::test_search_area_raises_when_one_area_fails` / `tests/cli/test_cli_commands.py::test_cli_returns_exit_code_3_for_fetch_failure` |
| US-02-1 `names-file既定値 + txt/csv入力` | `tests/domain/test_name_matching.py::test_load_hotel_names_reads_one_name_per_line` / `tests/domain/test_name_matching.py::test_load_hotel_names_reads_csv_name_url_and_options_columns` / `tests/cli/test_cli_commands.py::test_cli_search_names_uses_defaults_for_names_file_and_pref` |
| US-02-2 `local-filter 宿名部分一致/URL一致` | `tests/domain/test_name_matching.py::test_filter_hotels_by_names_partial_match_and_non_match` / `tests/domain/test_name_matching.py::test_filter_hotels_by_names_matches_when_candidate_is_hotel_url` / `tests/application/test_search_services.py::test_search_names_local_filter_accepts_hotel_url_candidates` |
| US-02-3 `0件でも正常/空JSON` | `tests/application/test_search_services.py::test_search_names_local_filter_returns_empty_when_no_match` / `tests/output/test_json_formatter.py::test_serialize_empty_records` |
| US-02-4 `照合後も重複排除維持` | `tests/application/test_search_services.py::test_search_names_local_filter_keeps_deduplication_after_match` |
| US-03-1 `coupon非公開(未対応)` | `tests/cli/test_cli_commands.py::test_cli_coupon_command_returns_exit_code_2` |
| US-03-2 `未対応要求はstderr+終了コード2` | `tests/cli/test_cli_commands.py::test_cli_coupon_command_returns_exit_code_2` |
