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

Open `ai/quarantine/presentation-demo/presentation-demo.html` only on the presentation computer. The adjacent JSON gives the fixed race IDs, prediction/actual comparison, concise pre-race reasons, and leakage controls.

## Integrity statement for the presentation

- Feature snapshots are constructed before results from that race day are applied. `finish_position`, time, final time, and time factor are excluded from features.
- Hyperparameter selection used validation dates only. The selected four are a subset of the chronological untouched test cohort, not a new model-selection sample.
- The demo uses actual historical races. It is retrospective and must not be represented as a prospective forecast or a new independent evaluation.

## Independent name verification and display restriction

`official-horse-names.csv` is a narrow local-display allowlist, not a copy of the research dataset. It records race ID, horse ID, name, official JRA source URL, confirmation timestamp, and scope. The generator displays a name only when this file has a matching `CONFIRMED` row; otherwise it stays hidden. `unconfirmed-horse-names.csv` is an ID-only follow-up list.

The KBlueLeaf dataset still permits internal storage and ML training only. Its name field is never used for demo display, and its rights record has not changed. The independent records were checked against JRA's 2019 official race-result PDFs. The JRA use notice identifies audiovisual/content reuse restrictions; this project copies neither PDF content, images, race narratives, nor data tables. A horse name is a registered identifier, which is distinct from copyright in a compiled race-result table. This is a scoped local-display assessment, not a legal opinion or permission for public redistribution. Do not upload the HTML, CSV, screenshots, or names to the website, API, slides distributed externally, or social media without separate rights review.
