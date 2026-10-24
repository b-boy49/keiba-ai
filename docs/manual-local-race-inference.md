# 手入力によるローカル競馬レース推論

この運用は有料データ契約・自動取得を使いません。レースカードと過去成績は、利用者が出典を確認したうえで手入力します。入力データ・照合結果・予測結果は `ai/quarantine/` のローカル研究領域にだけ保存します。

## 今回の固定対象

- `race_id`: `201905040610`
- 2019-10-19 東京10R（赤富士ステークス）、ダート 2,100m、12頭
- 既存 LightGBM の学習上限は 2015-06-06。対象日は時系列テスト領域であり、学習データには含まれません。
- JRA の公式成績表で12頭の馬名、枠番・馬番、騎手を目視確認する対象です。ここに馬名を転載して公開しません。

## 入力フォルダーを作る

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepare-tokyo-20191019-10-manual-input.ps1
```

保存先は `ai/quarantine/manual-input/tokyo-20191019-10/` です。既存ファイルは上書きしません。

| ファイル | 手入力する内容 |
| --- | --- |
| `official-race-card.csv` | 対象12頭の正式馬名、騎手名、枠番、馬番、斤量、`CONFIRMED`。結果着順は入れない。 |
| `horses.csv` | `horse_id` と正式馬名の1対1対応。 |
| `jockeys.csv` | `jockey_id` と正式騎手名の1対1対応。 |
| `past_performances.csv` | 対象レース日より前だけの実績。ここでのみ過去レースの着順を特徴量集計に使う。 |
| `source-review.json` | 出典URL、規約URL、確認日時、用途、確認状況。未確認なら `PENDING_REVIEW` のままにする。 |

CSVのヘッダーと1行の記入例は、作成される各テンプレートにあります。`official-race-card.csv` の `race_id` は全行 `201905040610`、`race_date` は全行 `2019-10-19`、`surface` は `DIRT`、`distance_m` は `2100` に固定します。

## 照合と取込

まず、馬名を既存SQLiteの馬マスターと**完全一致**で照合します。結果CSVには未一致・重複候補・入力IDとの衝突を個別行で出します。SQLiteに騎手マスターはないため、騎手は `JOCKEY_MASTER_UNAVAILABLE` と明示され、推測照合はしません。

```powershell
.\.venv\Scripts\python.exe -m ai.cli resolve-race-card-identities `
  --entries ai\quarantine\manual-input\tokyo-20191019-10\official-race-card.csv `
  --sqlite ai\quarantine\all_races_1990-2025.db `
  --output ai\quarantine\reports\tokyo-20191019-10-identity-review.csv
```

`horses.csv` / `jockeys.csv` のID・名称がカードと違う場合、推論コマンドは `horse ID/name mismatch` または `jockey ID/name mismatch` を出して停止します。過去成績に未登録のIDがあれば、そのIDを具体的に示して停止します。未来または当日成績を `past_performances.csv` に入れると、日時エラーで停止します。

権限が確認済みの提供元だけ、次の4コマンドで権限付き取込を実施できます。`<approved-provider-id>` を未確認の出典に置き換えてはいけません。`source-review.json` が `PENDING_REVIEW` の間は、公開取込・Vercel掲載をしません。

```powershell
.\.venv\Scripts\python.exe -m ai.cli import-entity-csv --input ai\quarantine\manual-input\tokyo-20191019-10\official-race-card.csv --output ai\quarantine\intake\tokyo-20191019-10\entries.csv --record-type entries --rights-manifest ai\rights\providers.json --provider-id <approved-provider-id>
.\.venv\Scripts\python.exe -m ai.cli import-entity-csv --input ai\quarantine\manual-input\tokyo-20191019-10\horses.csv --output ai\quarantine\intake\tokyo-20191019-10\horses.csv --record-type horses --rights-manifest ai\rights\providers.json --provider-id <approved-provider-id>
.\.venv\Scripts\python.exe -m ai.cli import-entity-csv --input ai\quarantine\manual-input\tokyo-20191019-10\jockeys.csv --output ai\quarantine\intake\tokyo-20191019-10\jockeys.csv --record-type jockeys --rights-manifest ai\rights\providers.json --provider-id <approved-provider-id>
.\.venv\Scripts\python.exe -m ai.cli import-entity-csv --input ai\quarantine\manual-input\tokyo-20191019-10\past_performances.csv --output ai\quarantine\intake\tokyo-20191019-10\past_performances.csv --record-type past_performances --rights-manifest ai\rights\providers.json --provider-id <approved-provider-id>
```

## 全頭AI推論

推論前に過去成績の欠損を可視化します。欠損値をゼロで捏造せず、LightGBMの欠損処理に渡します。

```powershell
.\.venv\Scripts\python.exe -m ai.cli race-history-coverage --spec ai\quarantine\config\tokyo-20191019-10.json --entries ai\quarantine\intake\tokyo-20191019-10\entries.csv --past-performances ai\quarantine\intake\tokyo-20191019-10\past_performances.csv --output ai\quarantine\reports\tokyo-20191019-10-history-coverage.csv --feature-as-of 2019-10-18T23:59:59Z

.\.venv\Scripts\python.exe -m ai.cli predict-configured-race-research --spec ai\quarantine\config\tokyo-20191019-10.json --entries ai\quarantine\intake\tokyo-20191019-10\entries.csv --past-performances ai\quarantine\intake\tokyo-20191019-10\past_performances.csv --horses ai\quarantine\intake\tokyo-20191019-10\horses.csv --jockeys ai\quarantine\intake\tokyo-20191019-10\jockeys.csv --model ai\quarantine\artifacts\candidate-20261023T110126Z --registry ai\quarantine\research-active.json --output ai\quarantine\predictions\tokyo-20191019-10-ranking.csv --feature-as-of 2019-10-18T23:59:59Z
```

出力は `reference_win_score` 降順、同点時は `horse_id` 昇順で自動順位化した全頭ランキングです。`finish_position` はモデル特徴量に渡らず、実績比較をする場合も推論後に別結合します。

## 発表会への掲載境界

`ai/quarantine/` のカード・照合表・特徴量・ランキングはローカル研究用で、Vercelへコピーしません。`source-review.json` と提供元権限の双方で `public_display: true` と `redistribution: true` を確認できたデータだけ、別途 `publish-prediction` を使えます。未確認またはローカル限定なら、ランキングCSVとローカルHTMLだけを確認し、サイトには掲載しません。
