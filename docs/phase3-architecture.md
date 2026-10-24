# Phase 3 システム設計

## 目的と非目的

目的は、**許諾済みの提供元**を差し替え可能にし、取得したレース情報の出典・鮮度・状態・失敗を追跡できる設計を固めることである。今回、外部サービスへの自動アクセス、スクレイピング、DB接続、定期ジョブは実装しない。

## 現在のPhase 2との接続

現在の `RaceRepository` は `list()` と `getById()` を提供し、`DemoRaceRepository` を実装している。Phase 3ではUIの呼び出し方を維持し、実データ取得をUIに混ぜない。

```text
Next.js UI / Route Handler
          │ RaceRepository（読取）
          v
DatabaseRaceRepository ──> PostgreSQL
          ^
          │ 正規化済みデータのみ
Ingestion Service / Fetch Job
          │
ProviderAdapter（契約済みの提供元ごと）
          │
許諾済みデータ提供元
```

`DemoRaceRepository` は開発・デモ用に残す。運用では環境設定ではなく、提供元契約の有効状態を確認した上で `DatabaseRaceRepository` を選ぶ。

## ProviderAdapter契約案

```ts
type ProviderCapabilities = {
  calendar: boolean; registrations: boolean; entries: boolean;
  odds: boolean; results: boolean; pastPerformances: boolean;
};

interface ProviderAdapter {
  readonly provider: string;
  readonly capabilities: ProviderCapabilities;
  fetchCalendar(input: { from: string; to: string }): Promise<RawPayload>;
  fetchRegistrations(input: RaceLocator): Promise<RawPayload>;
  fetchEntries(input: RaceLocator): Promise<RawPayload>;
  fetchOdds(input: RaceLocator): Promise<RawPayload>;
  fetchResult(input: RaceLocator): Promise<RawPayload>;
}
```

`RawPayload` は必要最小限に保管し、契約が原本保存を許さない場合は保持しない。`Validator` がスキーマ・重複・時点を検査し、`Normalizer` が既存の `Race` / `RaceEntry` とDBモデルへ変換する。UIが提供元固有のフィールドを直接参照しない。

## 取得ジョブと状態遷移

| トリガー | 取得対象 | 成功時状態 | 失敗時 |
|---|---|---|---|
| 週次・変更通知 | 開催カレンダー | `SCHEDULED` | 最終成功値を維持し、ジョブ失敗を表示 |
| 特別登録公開後 | 登録馬 | `REGISTERED` | 登録馬を確定馬として表示しない |
| 出馬表公開後 | 出走馬・騎手・斤量 | `ENTRIES_PUBLISHED` | 「出馬表発表待ち／更新失敗」を区別 |
| 枠順確定後 | 枠番・馬番 | `DRAW_CONFIRMED` | 前段階データを保持 |
| 契約範囲内の当日更新 | オッズ・馬場 | 状態は維持、時点スナップショット追加 | 古い値に更新時刻を付ける |
| レース後 | 結果・払戻 | `RESULT_FINAL` | 未確定のまま再試行 |

ジョブは冪等にする。`provider + external_id + payload_version/hash` をキーにし、同じ取得内容を重複登録しない。指数バックオフ、提供元別の同時実行数、契約で定めたレート制限を設定する。

## 信頼境界と表示規則

- `source`、`source_updated_at`、`fetched_at`、`ingestion_run_id`、`is_demo` をすべての公開候補レコードに持たせる。
- `is_demo = true` は実データと混ぜない。実データへの置換時もデモ履歴を上書きしない。
- 取得成功と公開可能は別判定にする。契約上公開不可のフィールドはDBにあってもAPI/UIから返さない。
- 提供元障害時は、未取得・最終成功日時・更新遅延を表示し、もっともらしい補完値を生成しない。
- オッズは `observed_at` がない値を公開しない。結果と発走前オッズは別リソースとして扱う。

## API境界案

公開APIはDBからの読み取りのみとし、取り込みやモデル学習を実行しない。

```text
GET /api/calendar?year=&month=
GET /api/races?date=&course=
GET /api/races/:raceId
GET /api/races/:raceId/entries
GET /api/races/:raceId/result
```

すべてのレスポンスに `status`, `source`, `updatedAt`, `fetchedAt`, `isDemo` を含める。データがない場合はHTTP 200の空配列または意味のある空状態を返し、推測データは返さない。管理・ジョブ起動は公開APIに置かず、認証済みの内部実行経路に限定する。

## 導入ゲート

1. 提供元から、取得・保存・学習・公開・キャッシュ・再配布を対象項目ごとに書面確認する。
2. 契約範囲を `ProviderPolicy` としてコード化し、未許可能力はAdapterから無効化する。
3. 小さい検証環境で1開催日だけを取り込み、状態・差分・時点情報を検査する。
4. 監査ログ、削除・保持期間、障害時の表示を確認する。
5. その後に公開APIと本番ジョブを有効化する。

## AI学習への影響

過去成績は予測日時点以前に確定した履歴だけを特徴量化する。出馬表、枠順、馬場、オッズは、それぞれの `observed_at` と `feature_snapshot_at` を比較して未来情報を除外する。Data Lab.等から入手できても、公開モデルの説明・学習成果物に含められる範囲は契約確認を要する。
