# Wikidata horse metadata integration (v0.9)

Last reviewed: 2026-10-23 (JST)

## Scope and licence boundary

Wikidata structured data is CC0. KEIBA AI uses it only as optional, human-operated horse metadata: entity matching, displayed horse name, birth date, parent links and any external identifiers that the item itself exposes. The source is recorded as `wikidata-cc0` in `ai/rights/providers.json` and each generated CSV has a hash-checked `.provenance.json` sidecar.

This is not a substitute for JRA data. It must not supply or infer a JRA race card, declared runners, gate/horse number, carried weight, jockey, trainer, past result, odds, result, payout, or a prediction. A Wikidata item may also be incomplete or incorrectly linked; a human must reconcile it with a separately authorised source before it is used in the target-race workflow.

## Field mapping

| KEIBA AI field | Wikidata source | Status / use |
|---|---|---|
| `horse_id`, `wikidata_id` | Item Q-id | Stable Wikidata-side identifier; it is not a JRA horse ID. |
| `horse_name` | Japanese label, then English label | Entity display/matching aid only. |
| `birth_date` | P569 (date of birth) | Optional; may be absent or have limited precision. |
| `sire_wikidata_id` | P22 (father) | Optional general parent relationship; requires human pedigree validation. |
| `dam_wikidata_id` | P25 (mother) | Optional general parent relationship; requires human pedigree validation. |
| `external_identifiers_json` | Claims with `external-id` datatype | Preserved as a source record, not treated as a licensed link to another dataset. |
| `source_url`, `retrieved_at` | Item URL / import timestamp | Provenance and freshness only. |

The importer never assumes that an item represents a Japanese racehorse. Operators give explicit Q-ids after manual review; it does not perform broad name search or bulk harvesting.

## API operation

`import-wikidata-horses` uses the documented Wikidata MediaWiki Action API (`wbgetentities`) for small, explicit batches. It requires a descriptive, contactable `--user-agent`; generic client user agents are rejected. It has a cache-first policy (`ai/cache/wikidata/`, ignored by Git), requests at most one uncached item per second, sets `maxlag=5`, and retries only transient 429/5xx/network failures with bounded exponential backoff. A terminal error stops before any output CSV is written. It is never invoked from Next.js or on a scheduled job.

```powershell
.\.venv\Scripts\python -m ai.cli import-wikidata-horses `
  --qid <reviewed-QID> --output ai/data/wikidata-horses.csv `
  --cache-dir ai/cache/wikidata `
  --user-agent "KEIBA-AI/0.9 (contact: your-contact@example.com)" `
  --rights-manifest ai/rights/providers.json
```

The command obtains only `ingest` and `internal_storage` authorisation from the ledger. It does not make a real-data training dataset or publication snapshot. Do not put personal contact data into a committed script or CSV.

## Data still required for Tokyo 9R, 2026-11-07

The site stays at `出走馬発表待ち` / `AI予想準備中` until all of the following are supplied from a separately rights-confirmed provider and pass the existing CSV validation:

1. The official/authorised final entry list: horse identity, jockey, gate, horse number, carried weight, publication timestamp and status.
2. Authorised historical race, entry, jockey and confirmed-result CSVs sufficient for a chronological train/holdout split.
3. The target horses' authorised past performances before the feature timestamp; the target's dirt 2100 m / Tokyo / jockey-pair features cannot be calculated without them.
4. An approved non-synthetic model, held-out metrics and calibration record; manual approval remains offline.
5. A frozen target prediction and, after the race, an authorised final result for performance comparison.

## Candidate data sets not adopted

| Candidate | Finding | Decision |
|---|---|---|
| Kaggle `takamotoki/jra-horse-racing-dataset` | Public project documentation identifies it as JRA race data, but the dataset page/original provider terms and rights for ML, display and redistribution have not been evidenced in this repository. | **Do not download or import.** |
| GitHub `tsukasaI/keiba-ai` | Its README points to the Kaggle dataset and describes a future live scraper; a repository licence does not establish rights in the underlying racing data. | **Do not import underlying data.** |
| GitHub `zliu43/netkeiba-scraper` / `shigeokitamura/netkeiba_scraper` | These projects explicitly describe scraping third-party pages. An OSS code licence does not permit use or redistribution of scraped source data. | **Do not run or import.** |
| GitHub `jon-makinen/open-horse-data` | Its own source table marks the reachable Japanese archive as having no stated licence and excludes several racing sources for licence reasons. | **Do not import Japanese records.** |

Reconsideration requires an immutable evidence link, review date, permission for each intended use (`ingest`, storage, training, display, redistribution), and a new approved provider entry. `--rights-confirmed` alone can never change this decision.

## Sources

- [Wikidata licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)
- [Wikidata data access guidance](https://www.wikidata.org/wiki/Help:Data_access)
- [Wikidata REST API user-agent requirement](https://www.wikidata.org/wiki/Wikidata:REST_API/Authentication/en)
- [open-horse-data source/licence inventory](https://github.com/jon-makinen/open-horse-data)
- [Kaggle-linked Japanese racing project documentation](https://github.com/tsukasaI/keiba-ai)
- [netkeiba scraper project design](https://github.com/zliu43/netkeiba-scraper/blob/main/project-design.md)
