# Hugging Face `KBlueLeaf/jp-racing-horse` 利用可否評価

調査日: 2026-10-23 (JST)  
対象: `all_races_1990-2025.db`（表示サイズ 1.04 GB）

## 結論

**限定的に社内情報解析へ使用、公開・再配布は未許可**。

Hugging Faceのリポジトリ画面には `apache-2.0` と表示されている。しかし、データセットカードのREADMEは空であり、元データの提供元、収集方法、元提供元が許す利用範囲、第三者データをApache-2.0として配布する権限を確認できる資料がない。リポジトリ上のライセンス表示だけでは、既存の権利台帳が求める「データ自体」の用途別権限の証跡にならない。

日本の著作権法30条の4および文化庁の説明を検討した結果、公開リポジトリからアクセス制限を回避せずに取得し、著作物の表現を享受・出力せずに統計的特徴を抽出する社内検証は、情報解析目的の利用として検討可能である。一方で、同条には権利者の利益を不当に害する場合の除外があり、原データ由来・データベース権・契約/規約・管轄の問題を解決するものではない。これは法的結論ではなく、リスクを留保した限定運用である。

このため、DBはGit管理外の `ai/quarantine/` にだけ取得し、`kblueleaf-jp-racing-horse-research` を「内部保存・学習のみ」の提供元として台帳に記録した。`public_display` と `redistribution` は false であり、公開スナップショットと公開モデル承認は機械的に拒否される。

## 確認できた公開情報

| 項目 | 確認結果 | 判断 |
|---|---|---|
| リポジトリ | `KBlueLeaf/jp-racing-horse` | 公開ページを確認 |
| 表示ライセンス | Apache-2.0 | リポジトリ表示。元データの権利証跡とは別問題 |
| 対象ファイル | `all_races_1990-2025.db`、1.04 GB | ファイル一覧を確認 |
| データセットカード | README.md あり、内容は空 | 出典・利用条件を確認不可 |
| データ内容 | Race/Horseテーブル、行数、対象期間、欠損、重複 | 読み取り専用で検査済み（下表） |
| 元データ出典・許諾 | 証跡なし | **未確認** |
| 学習・内部保存 | 30条の4を検討した限定的社内情報解析 | **研究専用・要リスク継続確認** |
| 表示・再配布 | 原データ権利が未解決 | **未許可** |

## 取得・品質検査結果

- 取得経路: Hugging Faceの公開 `resolve/main` URL。ログイン・アクセス制限回避・スクレイピングは行っていない。
- ファイルSHA-256: `7c6717f6f081f957721396d1e0e7296b4be3eeaa2fe1a657b41a4b5358474be9`。リポジトリ表示値と一致。
- Race: 450,648件、1990-01-05〜2025-03-27、`rid` 重複0、無効距離0、`horses` 欠損51、非JSON 0。
- Horse: 236,232件、`hid` 重複0、`born` / `name` / `info` / `races` の欠損は各4件。
- 東京競馬場コードは `05` と確認し、ダート2100mだけを時系列評価対象にした。

## 社内研究モデルの実行結果

日付単位で履歴を更新し、同日内・未来の結果を特徴量へ混入させない変換を実行した。当該レースの着順、走破時計、上がり、Netkeiba由来 `time_factor` は目的変数または結果後情報として特徴量から除外した。

| 項目 | 結果 |
|---|---:|
| 東京ダート2100m レース | 743 |
| 学習CSV行（出走馬） | 10,450 |
| 期間 | 1990-01-27〜2025-02-16 |
| 学習/検証/テスト | 日付で60%/20%/20%に時系列分割 |
| テストレース | 158 |
| テスト出走馬 | 2,275 |
| Top1的中率 | 19.62% |
| Top3内に勝馬を含む率 | 44.30% |
| Brier score / log loss | 0.0631 / 0.2417 |

このモデルは研究候補であり、校正済みの公開勝率ではない。`publication_permitted=false` のため、承認コマンドとサイト公開は拒否される。

## `db.py` のスキーマとKEIBA AI学習CSV対応

`db.py` はSQLiteの `Race` / `Horse` を定義する。`Race.horses` と `Horse.races` はJSON配列で、同じ履歴を非正規化して保持する設計である。`Race.horses` の説明には `time_factor` を「Netkeiba由来」と明記している。これにより、元データの少なくとも一部が第三者競馬サイトに由来することは確認できるが、取得の許諾は示されていない。

| DB項目 | 既存CSV/特徴量での候補 | 学習時の扱い |
|---|---|---|
| `Race.rid` | `race_id` | 一意性検査に使用可能 |
| `Race.date` | `race_date` | 時系列分割・`feature_as_of` 判定に使用可能 |
| `Race.place_id` | `course_id` / 東京フィルタ | コード表の別途確認が必要 |
| `Race.course` | `surface` | 0=ダート、1=芝と説明される |
| `Race.course_sit` | `track_condition` | 0=良〜3=不良。変換表が必要 |
| `Race.distance` | `distance_m` | 東京ダート2100m抽出に使用可能 |
| `Race.horses[][0]` | `horse_id` | レース内で展開して使用可能 |
| `Race.horses[][1]` | `finish_position` | **目的変数のみ**。当該レース特徴量に使用禁止 |
| `Race.horses[][2:4]` | 枠番・馬番相当 | 出馬表確定後だけ予測時特徴量候補 |
| `Race.horses[][4]` | `carried_weight_kg` 相当 | 出馬表確定後だけ予測時特徴量候補 |
| `Race.horses[][5:8]` | 馬体重・増減・走破時計 | 走破時計は結果後情報で使用禁止。馬体重系は公開時点の証跡が必要 |
| `Race.horses[][8:9]` | 上がり・time factor | **結果後情報で使用禁止**。time factorはNetkeiba由来と明記 |
| `Race.horses[][10]` | `jockey_id` | 騎手マスタ対応と予測時点の確認が必要 |
| `Horse.hid/name/born/info` | `horse_id` / `horse_name` / 馬属性 | 補助メタデータ候補。欠損・出典検査が必要 |
| `Horse.races` | `past_performances` | `race_date < feature_as_of` の履歴だけ集計する |

この対応は**権利が承認された場合に限る変換案**であり、現時点ではCSV変換・学習を実行していない。特に `ranking`、`time`、`finalt`、`time_factor` は当該レースの予測時点で未知であり、リーク防止のため特徴量にしてはならない。

## 由来の追跡結果

- READMEはライセンスメタデータのみ（31 bytes）で、出典・取得手段・利用条件の説明がない。
- コミット履歴はDBのアップロードと `db.py` 更新のみで、データカードや変更説明に原データ許諾へのリンクがない。
- `db.py` のコメントには `time_factor from Netkeiba` とある。一方、データセット作者からNetkeiba由来データを再配布・Apache-2.0で再許諾できることを示す資料は確認できない。
- ファイル名の対象期間は1990–2025だが、DBを保存していないため実際の最古・最新日、Race/Horse件数、欠損、重複は未確認であり、推測で記録しない。

## 無料候補の追加調査

| 候補 | 取得可否 | 利用条件の確認 | 結論 |
|---|---|---|---|
| Hugging Face `KBlueLeaf/jp-racing-horse` | 公開ダウンロード可能 | 上記のとおり原データ権利が未確認 | 保留・未取得 |
| JRA公開結果/PDF | ブラウザ閲覧・PDF掲載あり | AI学習、複製、再配布を許すオープンライセンス/APIは確認できない | 取得しない |
| 地方競馬情報サイトのCSV | 無料ダウンロード機能あり | 利用規約は掲載情報の無断転載・複製を禁じる | 取得しない |
| JRDB API | 技術APIあり | APIキー・認証キーが必要で無料・公開利用の権利は確認できない | 取得しない |
| Wikidata CC0 | API利用可能 | 馬メタデータのみ。JRA結果・出馬表・騎手履歴を代替しない | 補助メタデータに限定 |

## 実行しない作業

- サイトへの予想候補、予測スコア、元データの転載

2026-11-07の出走馬が確定していないため、この研究モデルから神奈川新聞杯の馬別順位を生成することもしない。

## 採用再審査に必要な証跡

1. データ作成者または元提供者を示す一次資料と、DB収録データの出典。
2. 元提供者が、内部保存、特徴量生成・AI学習、限定公開での予測表示、必要なら再配布を許す根拠。
3. 対象期間・テーブル定義・更新方法・収集方法の説明。
4. 取得日、固定コミットまたはハッシュ、確認者、許可資料URLを含む権利台帳の記録。
5. 権利承認後に限る、隔離保存先へのダウンロードとSQLite品質検査。

## 神奈川新聞杯への影響

2026-11-07 東京9R「神奈川新聞杯」は、出走馬・騎手・枠順・斤量が未確定であり、公開可能な実データモデルもない。よって現状は引き続き「出走馬発表待ち」「AI予想準備中」とし、架空の馬・着順・予測順位を表示しない。

## 参照

- [データセットカード](https://huggingface.co/datasets/KBlueLeaf/jp-racing-horse)
- [ファイル一覧](https://huggingface.co/datasets/KBlueLeaf/jp-racing-horse/tree/main)
- [db.py](https://huggingface.co/datasets/KBlueLeaf/jp-racing-horse/blob/main/db.py)
- [コミット履歴](https://huggingface.co/datasets/KBlueLeaf/jp-racing-horse/commits/main)
- [著作権法（e-Gov）](https://laws.e-gov.go.jp/law/345AC0000000048)
- [文化庁：30条の4とAI学習](https://www.bunka.go.jp/seisaku/chosakuken/hokaisei/h30_hokaisei/)
- [文化庁：不当な利益侵害の留保](https://www.bunka.go.jp/seisaku/bunkashingikai/chosakuken/pdf/94057901_01.pdf)
- [JRAの過去レース成績案内](https://www.jra.go.jp/faq/pop02/1_6.html)
- [地方競馬情報サイト利用規約](https://www.keiba.go.jp/terms.html)
- [JRDB APIの認証要件](https://jrdb-api.keiba.bigtime.world/docs)
- [既存のデータ利用方針](data-source-research.md)
- [権利台帳・取込運用](phase6a-operations.md)
