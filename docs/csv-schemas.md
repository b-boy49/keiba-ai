# Phase 6A CSVスキーマと品質ゲート

`ai/samples/` のCSVは**ヘッダーだけのテンプレート**であり、実在レースのデータではありません。各取込は提供元権利台帳、用途別権限、必須列、欠損、重複、型、範囲を検証します。不正なら出力を作らず停止します。

| 種別 | 必須キー | 主な検証 |
| --- | --- | --- |
| `races` | `race_id` | 日付、1〜24R、距離1〜10,000m、重複なし |
| `entries` | `race_id + horse_id` | 公開日時、馬・騎手・出走状態、重複なし |
| `past_performances` | `race_id + horse_id` | 日付、騎手、競馬場、着順、馬場、距離、重複なし |
| `horses` | `horse_id` | 馬名、重複なし |
| `jockeys` | `jockey_id` | 騎手名、重複なし |
| `results` | `race_id + horse_id` | 確定日時、正の着順、重複なし |
| `training_features` | `race_id + horse_id` | Phase 4特徴量、`feature_as_of <= race_date`、目的変数を特徴量に不使用 |

`training_features` の実データには `feature_as_of`（その特徴量を知り得たUTC時刻）が必須です。レース日時より後なら未来情報として拒否します。東京9R向けには、ダート2100mの成績・経験、東京実績、騎手との組み合わせを過去成績から集計する `build-target-features` を用意しています。CSV本体のSHA-256、入力SHA-256、権利台帳SHA-256、行数、提供元、証跡参照を `<output>.provenance.json` に保存し、変更後のCSVは学習に使えません。
