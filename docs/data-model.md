# Phase 3 データモデル・DB設計案

## 設計原則

- 内部IDと提供元の外部IDを分離する。
- レース、登録馬、確定出走馬、オッズ、結果、予想を上書きせず、時点を追跡する。
- 各データに出典・取得日時・公開可否・デモ区分を持たせる。
- オッズと結果、登録馬と確定出走馬を混同しない。

## 主テーブル

| テーブル | 主キー・主な列 | 目的 |
|---|---|---|
| `providers` | `id`, `name`, `contract_status`, `policy_version` | 提供元と利用条件の管理 |
| `racecourses` | `id`, `name`, `region` | 競馬場マスタ |
| `race_meetings` | `id`, `date_jst`, `racecourse_id`, `meeting_no`, `day_no` | 開催日 |
| `races` | `id`, `meeting_id`, `race_no`, `name`, `scheduled_start_at`, `surface`, `distance_m`, `class_name`, `status` | レースの現在状態 |
| `race_source_records` | `id`, `race_id`, `provider_id`, `external_id`, `source_updated_at`, `fetched_at`, `is_demo`, `publishable` | 出典・外部ID・鮮度 |
| `horses` | `id`, `canonical_name`, `birth_date`, `sex` | 馬マスタ |
| `jockeys` | `id`, `canonical_name` | 騎手マスタ |
| `race_entries` | `id`, `race_id`, `horse_id`, `jockey_id`, `entry_status`, `gate_no`, `horse_no`, `carried_weight_kg`, `published_at` | 登録・出走・取消を区別 |
| `entry_snapshots` | `id`, `race_entry_id`, `observed_at`, `source_record_id`, `payload_hash` | 出馬表の変更履歴 |
| `past_performances` | `id`, `horse_id`, `race_id`, `finish_position`, `finish_time`, `margin`, `track_condition`, `finalized_at` | AI用の確定履歴 |
| `odds_snapshots` | `id`, `race_id`, `horse_id`, `odds_type`, `value`, `observed_at`, `source_record_id` | 時点付きオッズ |
| `race_results` | `id`, `race_id`, `horse_id`, `finish_position`, `finish_time`, `margin`, `finalized_at` | 確定結果 |
| `payouts` | `id`, `race_id`, `bet_type`, `combination`, `amount_yen`, `finalized_at` | 払戻金（許諾時のみ） |
| `ingestion_runs` | `id`, `provider_id`, `job_type`, `started_at`, `finished_at`, `status`, `error_code`, `error_summary` | 取得実行・失敗監査 |

## 必須メタデータ

`race_source_records`、スナップショット、結果、払戻には少なくとも以下を保持する。

```text
provider_id        // データ提供元
external_id        // 提供元側の識別子（許される場合）
source_updated_at  // 提供元が示す更新日時
fetched_at         // KEIBA AIが取得した日時（UTC）
observed_at        // オッズ等を観測した日時（UTC）
is_demo            // デモデータか
publishable        // 契約上、公開API/UIへ返せるか
ingestion_run_id   // どのジョブで取得したか
payload_hash       // 差分・冪等判定用
```

## 制約・索引

- `races`: `meeting_id + race_no` を一意にする。
- `race_source_records`: `provider_id + external_id` を一意にする（提供元のIDが利用可能な場合）。
- `race_entries`: `race_id + horse_id` を一意にし、取消は削除せず `entry_status = SCRATCHED` に更新する。
- `odds_snapshots`: `race_id + horse_id + odds_type + observed_at` を一意にする。
- `race_results`: `race_id + horse_id` を一意にする。訂正があり得るため、元データの版・取得ジョブを保持する。
- `ingestion_runs`: `provider_id + job_type + started_at` に索引を付け、障害と更新遅延を監視する。

## 状態と公開規則

| レース状態 | `race_entries` | UIの扱い |
|---|---|---|
| `SCHEDULED` | なし | 開催予定。出馬表発表待ち |
| `REGISTERED` | `REGISTERED` のみ | 特別登録馬。確定出走馬として見せない |
| `ENTRIES_PUBLISHED` | 出走馬・騎手等 | 出馬表公開。枠番が空でも許容 |
| `DRAW_CONFIRMED` | 枠番・馬番あり | 枠順確定 |
| `IN_PROGRESS` | 出走情報を保持 | 開催中。オッズは観測時刻を必須 |
| `RESULT_FINAL` | 結果と紐付け | 結果確定。払戻は許諾取得後のみ |

## 既存TypeScript型との対応

Phase 2の `Race`、`RaceEntry`、`Horse`、`Jockey` はUI用の読み取りモデルとして維持する。DBのスナップショット・取得ジョブ・公開可否は新しい内部モデルで扱い、RepositoryがUI用に投影する。

```text
Provider raw data
  -> Validator / Normalizer
  -> relational tables + snapshots
  -> DatabaseRaceRepository
  -> Race / RaceEntry (UI read model)
```

これにより、DemoRaceRepositoryと将来のDatabaseRaceRepositoryが同じUI契約を実装できる。
