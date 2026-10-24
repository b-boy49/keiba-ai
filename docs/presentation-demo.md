# Company presentation: local historical prediction demo

The demo is an offline research artifact. It does not start a server, modify the web application, publish a snapshot, or invoke a public API. It selects exactly four races: the first four race IDs in chronological order from the existing untouched Tokyo dirt 2100m test cohort. This selection is fixed before predictions and race outcomes are read.

## Run locally

```powershell
$env:PYTHONPATH = "ai"
.\.venv\Scripts\python.exe -m ai.cli create-presentation-demo `
  --input ai\quarantine\kblueleaf_dirt_1800_2200_research.csv `
  --model ai\quarantine\artifacts\all-dirt-research-20261023T171338Z `
  --output-dir ai\quarantine\presentation-demo `
  --rights-manifest ai\rights\providers.json `
  --provider-id kblueleaf-jp-racing-horse-research `
  --horse-name-mapping ai\quarantine\presentation-demo\official-horse-names.csv `
  --include-horse-names
```

Open `ai/quarantine/presentation-demo/presentation-demo.html` only on the presentation computer. It is a standalone offline dashboard: four races are switched by date tabs or the previous/next buttons, and it does not call any server, API, or CDN. The adjacent JSON gives the fixed race IDs, prediction/actual comparison, concise pre-race reasons, and leakage controls.

## 全頭順位を当日に再計算する

次のコマンドは、保存済み順位を表示するのではなく、固定4レースの発走前特徴量を既存LightGBMへ再投入し、全出走馬のスコアと順位を毎回生成します。`finish_position` は推論に渡されず、画面の比較欄にだけ使われます。

```powershell
$env:PYTHONPATH = "ai"
.\.venv\Scripts\python.exe -m ai.cli rerun-historical-full-rankings `
  --input ai\quarantine\kblueleaf_dirt_1800_2200_research.csv `
  --model ai\quarantine\artifacts\all-dirt-research-20261023T171338Z `
  --horse-name-mapping ai\quarantine\presentation-demo\official-horse-names.csv `
  --output-dir ai\quarantine\presentation-demo
```

開くファイルは `ai\quarantine\presentation-demo\historical-2019-full-rankings.html` です。4レース計43頭を表示しますが、実名はJRA照合済み18頭だけです。残りは `非表示（JRA照合未完了）` と表示し、研究データの馬名で補完しません。

## Presentation-day launch

1. Run the command above on the presentation computer to refresh the isolated local artifact.
2. Open `ai\quarantine\presentation-demo\presentation-demo.html` directly in a modern browser. The initial race is 2019-10-14 (東京9R).
3. Use the date tabs or the previous/next buttons to move between the four fixed races. Explain the three separate badges: `本命的中` (AI 1位=実際の1着), `勝ち馬候補的中` (実際の1着がAI上位3頭), and `3着以内あり` (AI上位3頭のいずれかが実際の3着以内).
4. The 22.15% / 48.73% figures describe the existing 158-race chronological Tokyo dirt 2100m test, not the four displayed races.
5. To show the KEIBA AI homepage guide during local development only, start the site in a separate PowerShell session:

```powershell
$env:KEIBA_LOCAL_PRESENTATION_DEMO = "true"
npm.cmd run dev
```

6. Open the homepage from that local development server. The guide shows the local file path, but does not read, serve, or transmit the demo JSON/HTML.

`KEIBA_LOCAL_PRESENTATION_DEMO` is ignored outside development. The production build has no demo route, link, API response, or bundled presentation data.

## Integrity statement for the presentation

- Feature snapshots are constructed before results from that race day are applied. `finish_position`, time, final time, and time factor are excluded from features.
- Hyperparameter selection used validation dates only. The selected four are a subset of the chronological untouched test cohort, not a new model-selection sample.
- The demo uses actual historical races. It is retrospective and must not be represented as a prospective forecast or a new independent evaluation.

## Independent name verification and display restriction

`official-horse-names.csv` is a narrow local-display allowlist, not a copy of the research dataset. It records race ID, horse ID, name, official JRA source URL, confirmation timestamp, and scope. The generator displays a name only when this file has a matching `CONFIRMED` row; otherwise it stays hidden. `unconfirmed-horse-names.csv` is an ID-only follow-up list.

The KBlueLeaf dataset still permits internal storage and ML training only. Its name field is never used for demo display, and its rights record has not changed. The independent records were checked against JRA's 2019 official race-result PDFs. The JRA use notice identifies audiovisual/content reuse restrictions; this project copies neither PDF content, images, race narratives, nor data tables. A horse name is a registered identifier, which is distinct from copyright in a compiled race-result table. This is a scoped local-display assessment, not a legal opinion or permission for public redistribution. Do not upload the HTML, CSV, screenshots, or names to the website, API, slides distributed externally, or social media without separate rights review.
