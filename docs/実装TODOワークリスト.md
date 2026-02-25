# jalan-hotel-finder 実装TODOワークリスト（v1）

更新日: 2026-02-25  
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
  - 同一宿あたり最大3件を取得順で保持する重複排除関数
- 依存タスク: T00
- 前提条件: なし
- テスト:
  - クエリ差分の同一URL統合
  - 末尾スラッシュ有無の扱い
  - 同一宿で4件目以降を切り捨て、先頭3件を保持
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
- 前提条件: `python -m playwright install --with-deps chromium` 済み
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
  - 複数SML統合時に同一宿を最大3件まで保持
  - 1エリア失敗で終了コード3相当の例外
  - 取得0件でも正常完了
- 完了条件: `CLI仕様書 5.1` をユースケース単体で満たす。

### [x] T11: `search names` アプリケーションサービス
- 目的: 候補宿名ごとの keyword one-shot 取得結果に宿名照合を適用する。
- 成果物:
  - `search_names_keyword_one_shot()` ユースケース
  - `matched_name` 付与
- 依存タスク: T05, T10
- 前提条件: `list` は `keyword-one-shot` 固定
- テスト:
  - 1候補名=1リクエスト（ページ送りなし）
  - URL候補は keyword リクエスト対象外
  - 0件時も正常終了
  - 照合後も同一宿あたり最大3件保持を維持
- 完了条件: `CLI仕様書 5.2` を満たす。

### [x] T12: text-list出力整形（stdout固定）
- 目的: 出力仕様をCLIから分離して固定する。
- 成果物:
  - レコード列→人間向けリスト文字列のフォーマッタ
  - 必須4項目（宿名/URL/プラン名/価格）の出力整合
- 依存タスク: T10, T11
- 前提条件: なし
- テスト:
  - `search area` 形式
  - `list` 形式
  - 0件時メッセージ出力
- 完了条件: `CLI仕様書 7.1/7.2` を満たす。

### [x] T13: Typer CLI実装（`area` / `list`）
- 目的: ユースケースをCLIコマンドとして公開する。
- 成果物:
  - `jalan-search area`
  - `jalan-search list`
- 依存タスク: T02, T10, T11, T12
- 前提条件: なし
- テスト:
  - `CliRunner` で成功系（終了コード0）
  - 入力不備（終了コード2）
  - 取得失敗（終了コード3）
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
  - text-list出力のスナップショット
- 完了条件: `CLI仕様書 5` の全項目に対応テストが存在する。

### [ ] T15: `search area` の本格並列化（エリア単位）
- 目的: `area` の実行時間短縮のため、SMLエリア単位の並列処理を導入する。
- 成果物:
  - エリア単位でのタスク並列実行
  - `stop` ポリシー維持（1エリア失敗で終了コード3）
- 依存タスク: T10, T13
- 前提条件: レート制御（待機・同時実行上限）の再調整方針を定義すること
- テスト:
  - `並列数制約` を満たしつつエリア単位で並列化される
  - 1エリア失敗時に他タスクを停止し終了コード3相当の例外となる
- 既存の `同一宿判定（最大3件保持）` / `終了コード` の回帰がない
- 完了条件: `CLI仕様書 5.1(5)(6)` を維持したまま体感実行時間が改善する。

### [x] T16: US-01/US-02障害是正とE2E回帰防止
- 目的: 実環境で発生した `area` 停止問題と `list` 空配列問題を是正し、E2Eで再検知できる状態にする。
- 成果物:
  - `area.xml` 展開時の固定除外SML適用（初期値: `SML_013508`）
  - `openYadoSyosai('NNNNNN',...)` 形式と現行DOMクラス対応の抽出改善
  - mocked契約テストfixtureの現行DOM化
  - Live E2Eの非空・期待レコード必須化
- 依存タスク: T04, T06, T11, T14
- 前提条件: 2026-02-24観測で `SML_013508` が恒常的にエラー画面を返すことを確認済み
- テスト:
  - `resolve_sml_codes_for_prefecture` が `SML_013508` を除外
  - `openYadoSyosai` fixture から `hotel_name/url/plan/price` を抽出
  - `search_names_keyword_one_shot` がCSV読込経路でURL一致 `matched_name` を再現
  - Live E2Eで `area/list` の空配列通過を禁止
- 完了条件: `US-01/US-02` 既知障害の再現コマンドが解消し、回帰をテストで検知できる。

### [x] T17: `--pref` のカンマ区切り複数指定対応
- 目的: 都道府県入力を省力化し、1回の `--pref` 指定で複数県を受理できるようにする。
- 成果物:
  - `--pref` 値の正規化（`,` 分割、前後空白除去、空要素除外）
  - `area` / `list` で共通の入力正規化を適用
- 依存タスク: T02, T13
- 前提条件: 既存仕様の `--pref` 複数回指定互換を維持すること
- テスト:
  - `tests/cli/test_cli_commands.py::test_cli_search_area_accepts_comma_separated_prefectures`
  - `tests/cli/test_cli_commands.py::test_cli_search_names_accepts_comma_separated_prefectures`
- 完了条件: `CLI仕様書 6.2/6.3` の `--pref` 入力が `--pref 北海道,青森県` 形式で受理される。

### [x] T18: `--maxPrice`（予算上限）対応
- 目的: `area` / `list` 両コマンドで予算上限指定を受理し、検索URLへ反映する。
- 成果物:
  - `SearchAreaInput` / `SearchNamesInput` に `max_price` を追加
  - `area` / `list` CLIに `--maxPrice` オプションを追加
  - `maxPrice` のURL付与（指定時のみ）
- 依存タスク: T02, T03, T11, T13
- 前提条件: 未指定時は無制限（従来挙動）を維持すること
- テスト:
  - `tests/application/test_input_models.py::test_rejects_negative_max_price_for_search_area`
  - `tests/application/test_input_models.py::test_rejects_negative_max_price_for_search_names`
  - `tests/application/test_query_builder.py::test_build_search_area_url_includes_max_price_when_max_price_is_specified`
  - `tests/application/test_query_builder.py::test_build_keyword_search_url_includes_max_price_when_max_price_is_specified`
  - `tests/application/test_search_services.py::test_search_names_keyword_one_shot_passes_max_price_to_keyword_url`
  - `tests/cli/test_cli_commands.py::test_cli_search_area_accepts_max_price_option`
  - `tests/cli/test_cli_commands.py::test_cli_search_names_accepts_max_price_option`
- 完了条件: `--maxPrice` 指定時のみ `maxPrice` が付与され、未指定時は既存挙動を維持する。

### [x] T19: `list` の候補CSV `優先オプション` を keyword検索条件へ反映
- 目的: `list` 実行時に候補CSV `優先オプション` を検索条件へ反映し、`area` と同系統の `care*` 条件指定を可能にする。
- 成果物:
  - `優先オプション`（`care-kakenagashi|care-bath-rent|care-private-openair`）の解析・検証
  - 候補宿名ごとの keyword URL に `careKake/careBathRent/carePribateBath` を付与
  - `list` keyword URL に `checkin/adults/nights/meal/maxPrice` を反映
  - 未対応 `優先オプション` 検出時は終了コード `2`
- 依存タスク: T02, T03, T11, T13
- 前提条件: 候補CSVは `data/candidate_hotels.csv` 固定、`list` は one-shot 方針を維持すること
- テスト:
  - `tests/domain/test_name_matching.py::test_load_preferred_options_by_name_reads_supported_tokens`
  - `tests/domain/test_name_matching.py::test_load_preferred_options_by_name_rejects_unsupported_token`
  - `tests/application/test_query_builder.py::test_build_keyword_search_url_includes_stay_and_preferred_options_when_specified`
  - `tests/application/test_search_services.py::test_search_names_keyword_one_shot_applies_csv_preferred_options_to_keyword_url`
  - `tests/application/test_search_services.py::test_search_names_keyword_one_shot_raises_for_unsupported_csv_preferred_option`
  - `tests/cli/test_cli_commands.py::test_cli_returns_exit_code_2_for_invalid_preferred_option`
- 完了条件: `list` で候補CSVの `優先オプション` が keyword URL に反映され、不正トークンは `終了コード2` で停止する。

### [x] T20: US-03 `coupon` 実装（クーポン名 + 指定日 + 都道府県）
- 目的: `coupon` コマンドを公開し、クーポン対象かつ宿泊可能な宿一覧を取得できるようにする。
- 成果物:
  - `SearchCouponInput` と `coupon` CLIオプションの追加（`--coupon-name`, `--coupon-source-url`, `--checkin`, `--pref`）
  - `couponName -> couponId` 解決（`discountCoupon/CAM...` HTML / `theme/coupon/kikaku` `area.json`）
  - 都道府県→LRG展開、`uww1405` クエリ生成、`idx` ページング追跡
  - `uww1405` DOM抽出（`jlnpc-searchResultsCassette`）と `yadNo` URL正規化
  - 終了コード運用（入力不備=2, 取得失敗=3）
- 依存タスク: T02, T03, T04, T06, T07, T10, T13, T14
- 前提条件: `coupon` はクーポン名完全一致でID解決すること
- テスト:
  - `tests/infrastructure/test_coupon_name_resolver.py`（解決/未一致/曖昧/JSON異常）
  - `tests/application/test_query_builder.py::test_build_coupon_search_url_maps_required_params`
  - `tests/application/test_pagination.py::test_extract_next_page_url_from_select_page_javascript`
  - `tests/infrastructure/test_hotel_card_extractor.py::test_extracts_coupon_uww1405_cards_by_yad_no_links`
  - `tests/application/test_search_services.py::test_search_coupon_keeps_up_to_three_plans_per_hotel_across_multiple_lrg`
  - `tests/cli/test_cli_commands.py::test_cli_search_coupon_success_exit_code_0`
  - `tests/cli/test_cli_commands.py::test_cli_search_coupon_returns_exit_code_2_for_coupon_name_not_found`
  - `tests/cli/test_cli_commands.py::test_cli_search_coupon_returns_exit_code_3_for_fetch_failure`
- 完了条件: `CLI仕様書 5.3` を満たし、`coupon` 正常系/入力不備/取得失敗の終了コードが仕様どおりである。

---

## 依存関係サマリ（簡易）
- 先行推奨: `T00 → T01 → (T02, T04, T05, T06, T08) → T03 → T07 → T09 → T10 → T11 → T12 → T13 → T14 → T15`
- 障害是正パス: `T04 + T06 + T11 + T14 → T16`
- 入力互換拡張パス: `T02 + T13 → T17`
- 予算上限拡張パス: `T02 + T03 + T11 + T13 → T18`
- 候補オプション反映パス: `T02 + T03 + T11 + T13 → T19`
- クーポン検索実装パス: `T02 + T03 + T04 + T06 + T07 + T10 + T13 + T14 → T20`
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
| US-01-1 `pref -> SML展開` | `tests/infrastructure/test_area_xml_resolver.py::test_resolves_sml_codes_for_representative_prefecture` / `tests/infrastructure/test_area_xml_resolver.py::test_excludes_fixed_blocked_sml_codes_from_results` / `tests/cli/test_cli_commands.py::test_cli_search_area_accepts_comma_separated_prefectures` |
| US-01-2 `ページネーション追跡` | `tests/application/test_pagination.py::test_build_next_page_url_increments_by_30` / `tests/integration/test_end_to_end_mocked.py::test_integration_us01_area_search_list_snapshot` |
| US-01-3 `hotel_name/url/plan/price出力` | `tests/infrastructure/test_hotel_card_extractor.py::test_extracts_required_fields_from_normal_html` / `tests/infrastructure/test_hotel_card_extractor.py::test_extracts_keyword_result_cards_from_open_yado_syosai_links` |
| US-01-4 `URLパス単位の同一宿判定 + 1宿最大3件` | `tests/domain/test_hotel_deduplication.py::test_deduplication_keeps_records_when_query_is_different_within_limit` / `tests/domain/test_hotel_deduplication.py::test_deduplication_limits_to_three_records_per_hotel_by_default` / `tests/application/test_search_services.py::test_search_area_keeps_up_to_three_plans_per_hotel_across_multiple_sml` |
| US-01-5 `parallel=1..10` | `tests/application/test_input_models.py::test_rejects_parallel_over_limit_for_search_area` / `tests/infrastructure/test_crawler.py::test_parallel_limit_is_respected_with_semaphore` |
| US-01-6 `1エリア失敗で停止(終了コード3)` | `tests/application/test_search_services.py::test_search_area_raises_when_one_area_fails` / `tests/cli/test_cli_commands.py::test_cli_returns_exit_code_3_for_fetch_failure` |
| US-02-1 `names-file既定値 + txt/csv入力` | `tests/domain/test_name_matching.py::test_load_hotel_names_reads_one_name_per_line` / `tests/domain/test_name_matching.py::test_load_hotel_names_reads_csv_name_url_and_options_columns` / `tests/cli/test_cli_commands.py::test_cli_search_names_uses_defaults_for_names_file_and_pref` / `tests/cli/test_cli_commands.py::test_cli_search_names_accepts_comma_separated_prefectures` |
| US-02-2 `keyword one-shot + 宿名部分一致/URL一致 + 候補オプション反映` | `tests/application/test_search_services.py::test_search_names_keyword_one_shot_fetches_each_keyword_once` / `tests/application/test_search_services.py::test_search_names_keyword_one_shot_uses_loaded_csv_candidates_for_url_match` / `tests/application/test_search_services.py::test_search_names_keyword_one_shot_applies_csv_preferred_options_to_keyword_url` / `tests/domain/test_name_matching.py::test_filter_hotels_by_names_partial_match_and_non_match` / `tests/domain/test_name_matching.py::test_filter_hotels_by_names_matches_when_candidate_is_hotel_url` / `tests/domain/test_name_matching.py::test_load_preferred_options_by_name_reads_supported_tokens` |
| US-02-3 `0件でも正常/該当なしメッセージ` | `tests/application/test_search_services.py::test_search_names_keyword_one_shot_returns_empty_when_only_url_candidates` / `tests/output/test_json_formatter.py::test_shows_message_when_no_records` |
| US-02-4 `照合後も同一宿判定 + 1宿最大3件維持` | `tests/application/test_search_services.py::test_search_names_local_filter_keeps_up_to_three_plans_after_match` / `tests/output/test_json_formatter.py::test_limits_plans_to_three_per_hotel_in_recommendation_order` |
| US-03-1 `coupon入力（クーポン名/起点URL/宿泊日/pref）受理` | `tests/application/test_input_models.py::test_accepts_valid_coupon_input` / `tests/application/test_input_models.py::test_rejects_empty_pref_for_search_coupon` / `tests/cli/test_cli_commands.py::test_cli_search_coupon_requires_pref_and_returns_exit_code_2` |
| US-03-2 `couponName->couponId解決（完全一致/未一致/曖昧）` | `tests/infrastructure/test_coupon_name_resolver.py::test_resolves_coupon_id_from_discount_coupon_page_html` / `tests/infrastructure/test_coupon_name_resolver.py::test_resolves_coupon_id_from_kikaku_area_json` / `tests/infrastructure/test_coupon_name_resolver.py::test_raises_when_coupon_name_is_not_found` / `tests/infrastructure/test_coupon_name_resolver.py::test_raises_when_coupon_name_is_ambiguous` |
| US-03-3 `uww1405取得 + idxページング + 同一宿最大3件` | `tests/application/test_query_builder.py::test_build_coupon_search_url_maps_required_params` / `tests/application/test_pagination.py::test_extract_next_page_url_from_select_page_javascript` / `tests/application/test_search_services.py::test_search_coupon_follows_next_page_urls` / `tests/application/test_search_services.py::test_search_coupon_keeps_up_to_three_plans_per_hotel_across_multiple_lrg` |
| US-03-4 `終了コード運用（0/2/3）` | `tests/cli/test_cli_commands.py::test_cli_search_coupon_success_exit_code_0` / `tests/cli/test_cli_commands.py::test_cli_search_coupon_returns_exit_code_2_for_coupon_name_not_found` / `tests/cli/test_cli_commands.py::test_cli_search_coupon_returns_exit_code_3_for_fetch_failure` |
