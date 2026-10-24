# 研究評価集計値の公開可否レビュー（2026-10-24）

## 結論

`Top1 22.15%`、`Top3 48.73%`、`158レース`は、現時点でVercelを含む公開サイトには掲載しない。公開可否は **確認待ち** であり、公開許可済みとは扱わない。

この結論は法律上の助言ではない。公開を行うには、上流データ権利者または権限を持つ提供元から、評価集計値を公開してよい旨の書面または明確な利用条件を取得して、台帳を更新する必要がある。

## 対象集計値と内部再現根拠

| 値 | 内部成果物 |
| --- | --- |
| Top1 22.15% | `winner_top1_accuracy = 0.22151898734177214` |
| Top3 48.73% | `winner_top3_recall = 0.4873417721518987` |
| 158レース | `races = 158` |

参照先は `ai/quarantine/artifacts/all-dirt-research-20261023T171338Z/metadata.json` の `test_metrics.model`。評価コードは `ai/keiba_ai/training.py` の `evaluate_scores` である。Top1は各レースの最高スコア馬が1着だった割合、Top3は各レースの上位3頭に1着馬が含まれた割合であり、馬券の3連単・3連複の的中率ではない。

## 提供元・規約の確認結果

1. [KBlueLeaf/jp-racing-horse のデータセットページ](https://huggingface.co/datasets/KBlueLeaf/jp-racing-horse)は `apache-2.0` と表示する。
2. [同リポジトリのREADME](https://huggingface.co/datasets/KBlueLeaf/jp-racing-horse/blob/main/README.md)は空で、上流のデータ取得元、権利者、再配布・集計値公表の条件を説明していない。
3. [同リポジトリのスキーマ](https://huggingface.co/datasets/KBlueLeaf/jp-racing-horse/blob/main/db.py)には、`time_factor` がNetkeiba由来であるとの記載がある。したがって、リポジトリ表示のライセンスだけでは、含まれる上流由来データおよびその派生集計値の公開まで確認できない。
4. [Hugging Face利用規約](https://huggingface.co/terms-of-service)は、他者コンテンツの利用がそのコンテンツに付随する条件に従うことを示しており、Hub上のライセンス表示自体が上流権利を保証するものではない。
5. Apache 2.0は、正当なライセンサーが許諾する「Work」について公開・再配布を認めるライセンスであるが、[原文](https://www.apache.org/licenses/LICENSE-2.0)上もライセンサーは著作権者またはその授権者と定義される。上流権限が未確認のため、この条件を満たすと確認できない。

## 元データと集計値の区別

集計値は元CSVをそのまま再配布するものではない。しかし、元データとモデル評価から導出した成果物であり、上流の利用条件が集計値の外部公表を許すかは、この調査だけでは確認できない。そのため「統計値だけなので自動的に公開可能」とは判断しない。

権利台帳 `ai/rights/providers.json` も、対象提供元の全レコード種別について `public_display: false` および `redistribution: false` としている。この台帳と矛盾しないよう、公開数値は復元しない。

## 公開する場合に必要な作業

1. 上流権利者または正規提供元から、評価集計値のウェブ掲載を含む利用許可を取得する。
2. 許可対象、対象期間、集計方法、公開範囲、確認日・証跡URLを権利台帳へ記録する。
3. 元CSVや個別予測をVercelへ置かず、許可済みの最小限の評価サマリーだけを検証済み成果物から読み込む。
4. 再現テストと公開前レビューを通過後にのみ、`確認中`を実数値へ変更する。
