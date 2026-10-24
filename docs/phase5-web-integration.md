# Phase 5: Python / Next.js integration

## Adopted connection method

The system uses a **batch publication boundary**, not a Python API process. An authorized operator trains and manually approves a model offline, then runs `publish-prediction` / `publish-performance`. Those commands write small JSON snapshots under `ai/published/`; Next.js route handlers read them on the server only.

This is free to operate locally, avoids exposing Python execution or storage credentials to browsers, and works without making requests to external racing sites. A deployed service can replace the local directory with an object-store/DB adapter without changing the public response contract.

## Public read API

| Method | Endpoint | Behaviour |
| --- | --- | --- |
| GET | `/api/ai/status` | Safe readiness state only |
| GET | `/api/races/:raceId/prediction` | Approved prediction snapshot or `NOT_READY` |
| GET | `/api/races/:raceId/analysis` | Approved model metadata/score notice or `NOT_READY` |
| GET | `/api/performance` | Saved real prediction/result aggregates or `NOT_READY` |

There are no public write, training, import, or approval endpoints. `raceId` is validated before it is used as a file name. The public schema uses `reference_win_score`, not `win_probability`.

Phase 6Bでは、これらの読み取りAPIを含むすべてのサイトAPIを共有パスワードのMiddleware認証で保護する。認証、学習、取込、承認を公開書き込みAPIへ追加しない。

## Publication gates

1. The data publisher supplies `--rights-confirmed` **and** a Phase 6A provider rights manifest containing evidence and purpose-specific permissions.
2. `active.json` must point to a manually approved model.
3. The model metadata and prediction rows must not contain synthetic data.
4. The prediction CSV model version must match the approved model.

Failure at any gate produces no published snapshot. If the snapshot is absent or invalid, all web pages show **AI予想準備中**. The performance publisher computes aggregates only from persisted prediction rows joined with persisted, confirmed result rows; it never invents a hit rate.

## Operational flow

`licensed source -> import CSV -> train/evaluate -> human approval -> predict -> publish snapshot -> Next.js read API`

For production, add authenticated internal jobs, durable storage, audit logs for approvals/publishing, snapshot retention, and a data-retention policy. Keep the publication job outside the public web runtime.
