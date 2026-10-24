# 2019-10-19 東京10R（赤富士ステークス）手動取込手順

対象は2019年10月19日（土）東京10R・赤富士ステークス、ダート2100mです。JRAの公式結果ページと開催成績PDFで開催日、競馬場、レース番号、距離および12頭のレースを確認できます。これは過去の再現用であり、2026年の新潟8Rや神奈川新聞杯とは別の隔離された対象です。

既存の全ダート研究用再推論では、このレースの12頭すべてについてモデル出力から順位を生成済みです。ただし、ここで示す手動取込経路は、出馬表と過去成績を利用許諾の確認後に人が入力して、同じく全頭推論するための独立した手順です。実際の着順は入力しません。

## 1. まず作るローカル入力

次のディレクトリを作成し、テンプレートをコピーして入力します。`ai/quarantine/` はGitと公開サイトから除外されています。

```
ai/quarantine/manual-input/tokyo-20191019-10/
  official-race-card.csv
  horses.csv
  jockeys.csv
  past_performances.csv
  source-review.json
```

| ファイル | 入力する内容 |
| --- | --- |
| `official-race-card.csv` | テンプレート `ai/samples/official-race-card.template.csv` の全列。公式出馬表の12頭を1頭1行で、馬名・馬番・枠番・騎手名・斤量・状態を転記する。`horse_id` と `jockey_id` は次の照合後に入力する。取消・除外は消さず、`CANCELLED` または `SCRATCHED` とする。 |
| `horses.csv` | `ai/samples/horses.template.csv`。照合済みの canonical horse ID と正式馬名のみ。 |
| `jockeys.csv` | `ai/samples/jockeys.template.csv`。照合済みの canonical jockey ID と正式騎手名のみ。 |
| `past_performances.csv` | `ai/samples/past_performances.template.csv`。各出走馬の**2019-10-19 より前**の利用許諾済み成績だけを入力する。対象レース自身の結果は入れない。 |
| `source-review.json` | `ai/samples/manual-source-review.template.json`。取得元、利用条件、確認日時、確認者を記録する。`PENDING_REVIEW` のままでは取込しない。 |

CSVの見出しと例はテンプレートの `REPLACE_...` を実在データで置換します。テンプレートの例そのものを取り込んではいけません。

## 2. ID照合

手入力した出馬表（ID欄が空でも可）を、読み取り専用の研究SQLiteに対して照合します。これは名前の完全一致だけを候補にし、推測IDや曖昧一致は作りません。

```powershell
.\.venv\Scripts\python.exe -m ai.cli resolve-race-card-identities `
  --entries ai\quarantine\manual-input\tokyo-20191019-10\official-race-card.csv `
  --sqlite ai\quarantine\all_races_1990-2025.db `
  --output ai\quarantine\reports\tokyo-20191019-10-identity-review.csv
```

`EXACT_MATCH` 以外の馬は `horses.csv` に入れず、正規のID対応資料で人が確認します。現SQLiteには騎手の名前マスターがないため、騎手は正規の対応表で人が確認して `jockeys.csv` に入力します。馬名だけの類似照合、IDの採番、別表記の自動統合は禁止です。

## 3. 権利確認後に隔離取込する

`source-review.json` は台帳を変更しません。利用条件を確認した責任者が `ai/rights/providers.json` に、対象レコード種別の `ingest` と `internal_storage` が明記された承認済み提供元を追加した後だけ、以下の `<approved-provider-id>` を実在のIDに置き換えて実行します。

```powershell
.\.venv\Scripts\python.exe -m ai.cli import-entity-csv --input ai\quarantine\manual-input\tokyo-20191019-10\official-race-card.csv --output ai\quarantine\intake\tokyo-20191019-10\entries.csv --record-type entries --rights-manifest ai\rights\providers.json --provider-id <approved-provider-id>
.\.venv\Scripts\python.exe -m ai.cli import-entity-csv --input ai\quarantine\manual-input\tokyo-20191019-10\horses.csv --output ai\quarantine\intake\tokyo-20191019-10\horses.csv --record-type horses --rights-manifest ai\rights\providers.json --provider-id <approved-provider-id>
.\.venv\Scripts\python.exe -m ai.cli import-entity-csv --input ai\quarantine\manual-input\tokyo-20191019-10\jockeys.csv --output ai\quarantine\intake\tokyo-20191019-10\jockeys.csv --record-type jockeys --rights-manifest ai\rights\providers.json --provider-id <approved-provider-id>
.\.venv\Scripts\python.exe -m ai.cli import-entity-csv --input ai\quarantine\manual-input\tokyo-20191019-10\past_performances.csv --output ai\quarantine\intake\tokyo-20191019-10\past_performances.csv --record-type past_performances --rights-manifest ai\rights\providers.json --provider-id <approved-provider-id>
```

`import-post-2025-results` は2025年以降専用なので、この2019年の再現には使いません。

## 4. 成績欠損を確認し、全頭を推論する

```powershell
.\.venv\Scripts\python.exe -m ai.cli race-history-coverage `
  --spec ai\quarantine\config\tokyo-20191019-10.json `
  --entries ai\quarantine\intake\tokyo-20191019-10\entries.csv `
  --past-performances ai\quarantine\intake\tokyo-20191019-10\past_performances.csv `
  --output ai\quarantine\reports\tokyo-20191019-10-history-coverage.csv `
  --feature-as-of 2019-10-18T23:59:59Z

.\.venv\Scripts\python.exe -m ai.cli predict-configured-race-research `
  --spec ai\quarantine\config\tokyo-20191019-10.json `
  --entries ai\quarantine\intake\tokyo-20191019-10\entries.csv `
  --past-performances ai\quarantine\intake\tokyo-20191019-10\past_performances.csv `
  --horses ai\quarantine\intake\tokyo-20191019-10\horses.csv `
  --jockeys ai\quarantine\intake\tokyo-20191019-10\jockeys.csv `
  --model ai\quarantine\artifacts\candidate-20261023T110126Z `
  --registry ai\quarantine\research-active.json `
  --output ai\quarantine\predictions\tokyo-20191019-10-ranking.csv `
  --feature-as-of 2019-10-18T23:59:59Z
```

`race-history-coverage` は馬ごとの過去走数と不足理由を出します。過去走がない馬は0に埋めず、LightGBMが許容する `NaN` のまま特徴量を作ります。canonical ID不一致、未来または同日成績、12頭未満・超過の確定出走馬、重複馬番、未承認の入力は停止条件です。スコア降順、同点はhorse ID昇順で順位を決め、`tokyo-20191019-10-ranking.csv` とその provenance に保存します。

## 5. 表示と公開範囲

ローカル用HTMLは次で生成します。

```powershell
.\.venv\Scripts\python.exe -m ai.cli create-live-race-dashboard `
  --spec ai\quarantine\config\tokyo-20191019-10.json `
  --entries ai\quarantine\intake\tokyo-20191019-10\entries.csv `
  --prediction ai\quarantine\predictions\tokyo-20191019-10-ranking.csv `
  --model-version candidate-20261023T110126Z `
  --provider-id kblueleaf-jp-racing-horse-research `
  --output ai\quarantine\presentation-demo\tokyo-20191019-10-live.html
```

開くのは `ai/quarantine/presentation-demo/tokyo-20191019-10-live.html` だけです。現行研究モデルと研究SQLiteの台帳は `public_display: false` / `redistribution: false` であり、パスワード付きVercelを含む公開配信には実名・順位・スコア・CSV・HTMLを掲載できません。Vercelには既存の公開可能な説明と集計指標だけを表示します。

## 公式確認先

- [JRA 2019年10月19日 東京10R 公式結果](https://sp.jra.jp/JRADB/accessS.html?CNAME=sw01sde1005201904061020191019%2FA1)
- [JRA 2019年 第4回東京第6日 成績PDF](https://www.jra.go.jp/datafile/seiseki/report/2019/2019-4tokyo6.pdf)
- [JRA 利用規約](https://www.jra.go.jp/use/)

公式ページの閲覧・転記可否と公開可否は別に確認します。ここに記録したURLは、CSV取込やVercel公開の承認を意味しません。
