# 新潟8R（2026-10-24）研究用・全頭予測手順

対象は新潟8R・3歳以上1勝クラス（若手騎手）、ダート1800mです。レース仕様は `ai/quarantine/config/niigata-20261024-08.json` に固定しています。公式出馬表は [JRA公式出馬表](https://www.jra.go.jp/JRADB/accessD.html?CNAME=pw01dde0104202604030820261024%2F43) を照合元とします。

この手順はローカル研究環境専用です。JRA画面を自動取得せず、公開API、`public`、Vercelへ研究データを渡しません。

## 準備する入力

利用権限が承認された提供手段で、10頭全員の `entries.csv`、`horses.csv`、`jockeys.csv`、`post-2025-results.csv` を作成してから、既存の `import-entity-csv` / `import-post-2025-results` を使い `ai/quarantine/intake/niigata-20261024-08/` に取り込みます。各CSVには provenance sidecar が必要です。

`official-race-card.template.csv` の必須項目は、race ID・日付・競馬場・レース番号・レース名・馬ID/馬名・騎手ID/騎手名・枠番・馬番・斤量・出走状態・掲載日時・公式URL・確認日時です。取消・除外は削除せず `CANCELLED` / `SCRATCHED` として記録します。今回の全頭順位付けには、CONFIRMED の10頭が必要です。

## ID照合

SQLiteのHorseマスターは読み取り専用で検査します。騎手氏名マスターはSQLiteにないため、騎手を名前だけで結合することはありません。まず次を実行し、`MATCHED_EXACT` 以外の馬と全騎手の対応を、権限を持つ運用者が別の承認済み対応表で確認してください。

```powershell
.\.venv\Scripts\python.exe -m ai.cli resolve-race-card-identities `
  --entries ai\quarantine\intake\niigata-20261024-08\entries.csv `
  --sqlite ai\quarantine\all_races_1990-2025.db `
  --output ai\quarantine\reports\niigata-20261024-08-identity-review.csv
```

このCSVは確認用であり、IDを発行・推測しません。Horseの完全一致、既存IDとの矛盾、候補なし、同名候補を区別します。

## 欠損と予測

過去成績がない馬の集計特徴量はNaNのままです。LightGBMが欠損を扱える仕様でも、canonical horse/jockey ID、正式出馬表、provenanceは必須であり、未照合なら推論しません。2025-03以降の成績の不足はレポートで馬単位に表示します。結果・発走後の情報、同日結果は入力拒否されます。

```powershell
.\.venv\Scripts\python.exe -m ai.cli build-race-features `
  --spec ai\quarantine\config\niigata-20261024-08.json `
  --entries ai\quarantine\intake\niigata-20261024-08\entries.csv `
  --past-performances ai\quarantine\intake\niigata-20261024-08\post-2025-results.csv `
  --output ai\quarantine\predictions\niigata-20261024-08.features.csv `
  --feature-as-of 2026-10-23T23:59:59Z

.\.venv\Scripts\python.exe -m ai.cli predict-configured-race-research `
  --spec ai\quarantine\config\niigata-20261024-08.json `
  --entries ai\quarantine\intake\niigata-20261024-08\entries.csv `
  --past-performances ai\quarantine\intake\niigata-20261024-08\post-2025-results.csv `
  --horses ai\quarantine\intake\niigata-20261024-08\horses.csv `
  --jockeys ai\quarantine\intake\niigata-20261024-08\jockeys.csv `
  --model ai\quarantine\artifacts\candidate-20261023T110126Z `
  --output ai\quarantine\predictions\niigata-20261024-08-ranking.csv `
  --feature-as-of 2026-10-23T23:59:59Z
```

出力は全10頭をスコア降順（同点はcanonical horse ID昇順）で並べ、予測日時、モデル版、provenanceを併記します。新潟ダート1800mは東京ダート2100m以外の未検証条件であり、この注意書きは出力に残ります。

## 発表会用ローカル画面

以下は外部通信なしで、入力待ち状態も含めて表示するHTMLを作ります。予測後は `--entries` と `--prediction` を加え、モデル版と提供者IDも指定します。

```powershell
.\.venv\Scripts\python.exe -m ai.cli create-live-race-dashboard `
  --spec ai\quarantine\config\niigata-20261024-08.json `
  --output ai\quarantine\presentation-demo\niigata-20261024-08.html
```

生成後に `ai\quarantine\presentation-demo\niigata-20261024-08.html` をブラウザで直接開きます。これはNext.jsのURLではなく、研究用ローカルHTMLです。
