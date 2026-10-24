# All-dirt research experiment (internal only)

## Scope and isolation

- Preserved baseline: `ai/quarantine/artifacts/candidate-20261023T110205Z`
  (Tokyo dirt 2100m-only LightGBM).  It was not overwritten or promoted.
- Model: `ai/quarantine/artifacts/all-dirt-research-20261023T171338Z`
- Training data: `ai/quarantine/kblueleaf_dirt_1800_2200_research.csv`
  (other dirt races in the target-compatible 1800–2200m range)
- The dataset, model, and report remain in `ai/quarantine/`.  The provider
  provenance permits only ingestion, internal storage, and ML training.  It
  explicitly denies public display and redistribution.
- No Next.js route, public snapshot, registry approval, or page was changed.

## Leakage controls

- Historical aggregates use only races strictly before the race date.
- Results from a date are applied only after every race on that date has been
  transformed, preventing same-day-result leakage.
- `finish_position` is target-only. Odds, final time, time factors, and every
  other result-time field are excluded.
- Hyperparameters were selected on the chronological validation period only.
  The final test interval was not used for feature or parameter selection.

## Data and split

| Set | Races / rows | Period |
| --- | ---: | --- |
| All-dirt source | 26,981 / 322,876 | 1990-01-27 to 2025-02-16 |
| Target cohort (Tokyo dirt 2100m) | 743 / 10,450 | same source period |
| Train | all dirt through 2015-06-06 | historical cutoff |
| Validation | 154 / 2,224 target rows | 2015-06-07 to 2019-06-23 |
| Untouched test | 158 / 2,275 target rows | 2019-10-14 to 2025-02-16 |

## Feature set

Pre-race features: distance; venue; going; gate; horse number; declared
carried weight; field size; recent 3/5 race finish aggregates and win/top-3
rates; same-distance experience; Tokyo/current-venue history; jockey win/top-3
rate; horse-jockey history; and days since the last run.  Class and horse age
are not present in the authorized source schema, so they were not fabricated
or used.

## Results on the unchanged test set

| Model | Top1 | Top3 | Brier | Log loss |
| --- | ---: | ---: | ---: | ---: |
| Original Tokyo-2100 LightGBM baseline | 19.62% | 44.30% | 0.06308 | 0.24173 |
| Recent-finish baseline | 15.19% | 45.57% | 0.06277 | 0.24124 |
| Selected all-dirt research LightGBM | **22.15%** | **48.73%** | **0.06255** | **0.23830** |

The selected configuration is `num_leaves=28`, `n_estimators=220`,
`learning_rate=0.04`, `min_child_samples=45`, `subsample=0.85`, and
`colsample_bytree=0.95`.  It was selected using validation Top1, then Top3,
then log loss.  Relative to the original model it improves Top1 by 2.53 points,
Top3 by 4.43 points, Brier by 0.00052, and log loss by 0.00343.  Relative to
the recent-finish baseline it improves every reported metric (Top1 +6.96
points; Top3 +3.16 points).

## 2026-11-07 Tokyo 9R

This is the most promising research candidate, but it cannot truthfully name
1st–3rd candidates until a rights-authorized confirmed entry list, declared
jockey/weight/gate data, and pre-race performance history are supplied.  The
existing `build-target-features` command now emits compatible pre-race fields;
the candidate remains explicitly unapproved and cannot enter public APIs.
