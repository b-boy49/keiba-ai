# Phase 6A 運用手順

## 1. 提供元を審査する

`ai/rights/providers.json` に提供元、URL、ライセンス、確認日、確認資料URL、社内の確認参照ID、データ種別ごとの `ingest` / `internal_storage` / `ml_training` / `public_display` / `redistribution` を記録します。証跡・承認状態・用途の一つでも欠ければ既定で拒否します。

WikidataはCC0の補助メタデータ候補として台帳にありますが、許可範囲は `horses` のみです。JRA出馬表、結果、オッズ等を置き換えるためには使えません。APIを将来使う場合も、識別可能なUser-Agent、低頻度、キャッシュ、429時のバックオフを実装・運用してから、別途レビューします。本Phaseではネットワーク取得を実装していません。

Kaggle、GitHub、スクレイピング由来のCSVは、元データのライセンスと全用途の権限を証跡化するまで台帳を `APPROVED` にしてはいけません。

## 2. 取込

```powershell
.\.venv\Scripts\python -m ai.cli import-entity-csv --input <horses.csv> --output <approved-horses.csv> --record-type horses --rights-manifest ai/rights/providers.json --provider-id wikidata-cc0
.\.venv\Scripts\python -m ai.cli import-csv --input <features.csv> --output <approved-features.csv> --source-name <provider> --provider-id <provider-id> --rights-manifest <rights.json> --rights-confirmed
```

`--rights-confirmed` は操作の意図を示すだけで、台帳の証跡や用途別権限を代替しません。取込後のCSVと `.provenance.json` は対として保管します。

## v0.9: Wikidata horse metadata

Wikidata is limited to reviewed horse Q-ids and CC0 metadata. Run `import-wikidata-horses` only as a human-operated task with a descriptive contactable User-Agent. The importer caches raw responses, spaces uncached requests by one second, retries bounded transient failures, writes a provenance sidecar, and stops before a CSV is written on a terminal API error. It is not an entry/result/jockey importer and must not be used as a JRA data substitute. See `docs/wikidata-horse-integration.md`.

## 3. 学習・承認・公開

実データ学習は来歴付きCSVのみ受け付けます。時系列60/20/20分割で未使用期間を評価し、Brier score・log loss・Top-1・Top-3を保存します。承認には権利検証済み、非合成、全体100レース以上、未使用評価30レース以上、校正ホールドアウト記録が必要です。閾値を満たさない場合、画面は引き続き「AI予想準備中」です。

公開はPhase 5のJSON方式のままです。`predict` は予測CSVにもモデル版・学習提供元・ハッシュ付き来歴を保存します。公開表示・再配布の権限、予測CSV来歴、モデル来歴、結果CSV来歴を再検証し、提供元とハッシュが一致する場合のみ実行できます。
