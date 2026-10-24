# 2026-11-07 東京9R 神奈川新聞杯 本番手順

対象は固定で `tokyo-20261107-09`、東京9R・神奈川新聞杯・ダート2,100m・3歳以上2勝クラス・定量・14:25予定である。公式番組表は予定であり、JRAが案内する正式な出馬表を優先する。出走馬が確定するまで画面は「出走馬発表待ち」とする。

## CSV登録

利用権限・証跡・用途別許可を確認済みのCSVだけをPhase 6Aの取込コマンドで登録する。

```powershell
# 確定出走馬（騎手・枠番・馬番・斤量を含む）
.\.venv\Scripts\python -m ai.cli import-entity-csv --input <entries.csv> --output <approved-entries.csv> --record-type entries --rights-manifest <rights.json> --provider-id <provider>

# 過去成績（競馬場と騎手を含む）
.\.venv\Scripts\python -m ai.cli import-entity-csv --input <past.csv> --output <approved-past.csv> --record-type past_performances --rights-manifest <rights.json> --provider-id <provider>

# 確定出走馬と予測時点までの過去成績から特徴量を生成
.\.venv\Scripts\python -m ai.cli build-target-features --entries <approved-entries.csv> --past-performances <approved-past.csv> --output <target-features.csv> --feature-as-of <UTC日時>
```

この特徴量生成は、近3走、ダート2,100mの経験・平均着順、東京の出走数・平均着順、騎手の勝率、馬と騎手の組み合わせ実績、休養日数だけを使う。`feature_as_of`以後とレース当日以後の過去成績は拒否する。馬場・オッズなど未確定情報は入力しない。

## 予想・保存・結果照合

承認済みの実データモデルがある場合のみ、生成済み特徴量を `predict` し、予測CSVの来歴を保存する。その後、権利台帳・モデル来歴・予測出力来歴を満たす場合のみPhase 5の公開JSONにできる。出力には `reference_win_score`、1〜3着候補、特徴量時点、使用項目を記録する。

レース後は、権利確認済みの確定結果CSVを `results` として取込み、保存済み予測CSVと `publish-performance` で比較する。予測CSVは結果を見て上書きしない。

## 現在の停止条件

現在、確定出走馬CSV、権利確認済みの過去成績CSV、承認済み実データモデル、確定結果CSVのいずれも登録されていない。そのため公開画面はAI予想準備中のままであり、馬名・騎手・枠順・順位・スコアを表示しない。
