# KEIBA AI prediction foundation

This directory is an offline, batch-only ML foundation. It does not fetch from external sites. Phase 5 adds an explicit, human-operated publication command; Next.js reads its JSON output server-side and never invokes Python from a public request.

## Wikidata horse metadata (human-operated)

The only network-capable command is an explicit, small-batch Wikidata importer for reviewed Q-ids. It is CC0 horse metadata only, is cache-first, requires a descriptive contactable User-Agent, and is never called by the website. It cannot import entries, results, odds, jockey data, or make a public prediction.

```powershell
.\.venv\Scripts\python -m ai.cli import-wikidata-horses --qid <reviewed-QID> --output ai/data/wikidata-horses.csv --cache-dir ai/cache/wikidata --user-agent "KEIBA-AI/0.9 (contact: your-contact@example.com)" --rights-manifest ai/rights/providers.json
```

Read [the Wikidata integration design](../docs/wikidata-horse-integration.md) before using it. Do not run it for the 2026-11-07 Tokyo 9R until a reviewed horse Q-id is available from an authorised entry list.

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r ai\requirements.txt
```

## Safe demo flow

```powershell
.\.venv\Scripts\python -m ai.cli make-synthetic --output ai/data/synthetic_races.csv
.\.venv\Scripts\python -m ai.cli train --input ai/data/synthetic_races.csv
.\.venv\Scripts\python -m ai.cli predict --model <candidate-directory> --input ai/data/synthetic_races.csv --output ai/data/predictions.csv
.\.venv\Scripts\python -m ai.cli evaluate --predictions ai/data/predictions.csv
```

All synthetic outputs carry `is_synthetic=true` and are **not real horse-racing predictions**. The `reference_win_score` is a calibrated reference score, not a validated public win probability.

## Licensed CSV import

Only import data whose collection, storage, training, and publication rights are confirmed.

```powershell
.\.venv\Scripts\python -m ai.cli import-csv --input <licensed.csv> --output ai/data/licensed.csv --source-name <provider> --rights-confirmed
```

The importer intentionally rejects input without `--rights-confirmed`. Phase 6A additionally requires an approved provider record, evidence references, and the required purpose permissions in `ai/rights/providers.json`; a self-declaration alone does not authorize any data.

See [the Phase 6A operations guide](../docs/phase6a-operations.md) and [CSV schemas](../docs/csv-schemas.md). The `ai/samples/` CSV files are header-only templates, never real racing data.

## Phase 5 publication boundary

Only a manually approved, non-synthetic model trained on data with confirmed publication rights can be exported. This command is intentionally offline and is **not** exposed as a web API.

```powershell
.\.venv\Scripts\python -m ai.cli publish-prediction --registry ai/artifacts/active.json --predictions <real-predictions.csv> --race-id <race-id> --source-name <licensed-provider> --rights-confirmed
.\.venv\Scripts\python -m ai.cli publish-performance --predictions <saved-real-predictions.csv> --results <confirmed-results.csv> --source-name <licensed-provider> --rights-confirmed
```

The output is `ai/published/`. It must not contain synthetic results. `reference_win_score` remains a reference score until its calibration is independently validated.
