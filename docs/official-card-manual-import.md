# Official race-card manual import

When no licensed API or officially authorised machine-readable feed is available, an operator may transcribe an official JRA race card into `ai/samples/official-race-card.template.csv`. This is an input operation, not a prediction operation.

Before import, compare every row with the official card: race date, course, race number/name, surface/distance, horse name, canonical horse ID, jockey, gate, horse number, declared weight, and status. Include `SCRATCHED`/`EXCLUDED` entries rather than deleting them. Do not infer a missing name or number from historical data.

Only after an authorised provider and rights record have been approved may the existing `import-entity-csv` command copy the card into `ai/quarantine/intake/`. The prediction pipeline must reject a missing canonical ID, duplicate horse number, incomplete card, non-confirmed runner, missing provenance, future performance, or ID/name mismatch.

The current research model is evaluated only for Tokyo dirt 2100m. A dirt 1800–2200m card can be inferred only as an internal, explicitly **unvalidated-condition** demonstration. Turf cards must not be submitted to this model.
