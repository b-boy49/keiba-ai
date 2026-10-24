# Phase 4 AIモデル管理設計

## 安全な運用原則

- 学習は利用権限のあるデータ、または明示された合成データだけを使う。
- 合成データ由来モデルは `contains_synthetic=true` と記録し、`approve` コマンドでアクティブ化できない。
- モデルの出力は、時系列の外部テストと確率校正が十分に検証されるまで `reference_win_score`（参考スコア）として扱う。公開UIの勝率には接続しない。
- 新モデルは必ず候補として保存する。自動採用しない。

## バージョンと成果物

`ai/artifacts/candidate-YYYYMMDDTHHMMSSZ/` に以下を保存する。

- `model.joblib`: LightGBM分類器、校正器、固定した特徴量列、メタデータ
- `metadata.json`: 学習日時、データ源、合成データ有無、来歴ハッシュ、時系列分割境界、Brier score、log loss、Top-1/Top-3評価、校正状態、承認状態

`active.json` は手動承認済みモデルだけを指す。合成データ候補、権利来歴のない候補、全体100レースまたは未使用評価30レースに満たない候補は承認コマンドが拒否する。

## 時系列検証

レース日単位で古い順に 60%（学習）/ 20%（校正）/ 20%（最終テスト）へ分割する。同一レースの馬を異なる分割に入れない。`finish_position` は目的変数だけに使用し、特徴量には含めない。

## 再学習判定

`retrain` は候補モデルを作るだけである。既存メタデータと比較する場合、Brier score改善かつTop-1精度非悪化を「手動承認を検討可能」とする。これも自動採用条件ではない。データ品質、期間、欠損、確率校正、実運用の妥当性を人が確認してから承認する。

## CLI

```text
python -m ai.cli make-synthetic --output ...
python -m ai.cli import-csv --input ... --output ... --source-name ... --rights-confirmed
python -m ai.cli train --input ...
python -m ai.cli predict --model ... --input ... --output ...
python -m ai.cli evaluate --predictions ... --input ...
python -m ai.cli retrain --input ... --active-metadata ...
python -m ai.cli approve --candidate ...
```

この基盤はネットワークアクセスやJRAデータ取得機能を持たない。実データ接続はPhase 3の利用許諾ゲート通過後に、ProviderAdapterとDB経由で追加する。
