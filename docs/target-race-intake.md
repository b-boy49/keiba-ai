# 2026-11-07 東京9R・神奈川新聞杯: internal prediction intake

No horse name, entrant, or predicted rank is stored in this repository. The race remains unpredicted until the confirmed card and rights-approved history are imported.

## Files to fill in

- `ai/samples/kanagawa-shimbun-hai-20261107.entries.template.csv` — confirmed entrants only. Use canonical horse/jockey IDs, status `CONFIRMED`, gate, horse number, declared weight, and the card publication timestamp.
- `ai/samples/post-2025-results.template.csv` — race results dated from 2025-03-01 onward, using the same canonical IDs.
- Existing `ai/samples/horses.template.csv` and `ai/samples/jockeys.template.csv` — the canonical ID/name lookup tables. A name that does not exactly match its ID is rejected.

Both input feeds must be rights-approved before copying the checked files to `ai/quarantine/intake/`. The commands write approved copies and provenance sidecars; do not manually edit those copies.

```powershell
python -m ai.cli import-post-2025-results --input ai/samples/post-2025-results.template.csv --output ai/quarantine/intake/post-2025-results.csv --horses ai/quarantine/intake/horses.csv --jockeys ai/quarantine/intake/jockeys.csv --rights-manifest ai/rights/providers.json --provider-id <approved-provider>
python -m ai.cli import-entity-csv --input ai/samples/kanagawa-shimbun-hai-20261107.entries.template.csv --output ai/quarantine/intake/entries.csv --record-type entries --rights-manifest ai/rights/providers.json --provider-id <approved-provider>
python -m ai.cli target-history-coverage --entries ai/quarantine/intake/entries.csv --past-performances ai/quarantine/intake/post-2025-results.csv --output ai/quarantine/reports/kanagawa-history-coverage.csv --feature-as-of 2026-11-06T00:00:00Z
```

`kanagawa-history-coverage.csv` explicitly reports `no_prior_performance` and `no_result_since_2025_03_01`. Resolve every reported gap before relying on a prediction.

Once the card, lookup tables, and history have approved provenance, run the internal-only command. The output path must remain below `ai/quarantine/`; it emits only ranks 1–3 and cannot publish to the website/API.

```powershell
python -m ai.cli predict-target-research --entries ai/quarantine/intake/entries.csv --past-performances ai/quarantine/intake/post-2025-results.csv --horses ai/quarantine/intake/horses.csv --jockeys ai/quarantine/intake/jockeys.csv --model ai/quarantine/artifacts/<approved-research-model> --output ai/quarantine/predictions/tokyo-20261107-09-top3.csv --feature-as-of 2026-11-06T00:00:00Z
```

Feature construction rejects any past-performance row after `feature-as-of` or on/after race day. The held-out Tokyo dirt 2100m test is not consulted or reused for model selection by this workflow.
