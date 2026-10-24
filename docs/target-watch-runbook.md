# Target-race offline watcher

`watch-target-research` does not fetch, scrape, or upload data. It checks only the rights-tracked CSVs already placed in `ai/quarantine/intake/` and writes all status, logs, coverage reports, and predictions under `ai/quarantine/`.

## Required approved inputs

Place these existing rights-checked CSVs and their `.provenance.json` sidecars in `ai/quarantine/intake/`:

- `entries.csv` — 11/5 entries may use a non-`CONFIRMED` status. Prediction waits. On 11/6, each runner must be `CONFIRMED` and have a positive `gate_no` and `horse_no`.
- `post-2025-results.csv` — authorised results since 2025-03-01; never include a result at or after the feature timestamp or target race date.
- `horses.csv`, `jockeys.csv` — reviewed canonical-ID maps. Aliases, duplicate names, and mismatches stop processing.

The normal import commands in `docs/target-race-intake.md` create these files and provenance records. Do not place raw web downloads in this folder.

## Manual run

```powershell
cd C:\keiba-ai
.\scripts\run-target-watch.ps1 -FeatureAsOf "2026-11-06T00:00:00Z"
```

The watcher reports one of `DATA_WAITING`, `ENTRY_WAITING`, `GATE_WAITING`, `DATA_INSUFFICIENT`, `PREDICTION_CURRENT`, `PREDICTION_COMPLETE`, or `PROCESSING_FAILED` in `ai/quarantine/predictions/target-prediction-status.json`.

## Task Scheduler

Create a task that runs every 30 minutes from 2026-11-05 through 2026-11-06:

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\keiba-ai\scripts\run-target-watch.ps1"
$trigger = New-ScheduledTaskTrigger -Once -At "2026-11-05 09:00" -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Days 2)
Register-ScheduledTask -TaskName "KEIBA AI Target Watch" -Action $action -Trigger $trigger -Description "Offline CSV watcher for the internal research target race"
```

The task runs only while the PC is powered on and able to run scheduled tasks. It does not wake a powered-off computer. Review `ai/quarantine/logs/` after a failure; the next run safely retries. The input hash prevents duplicate prediction for unchanged inputs; changed CSVs cause a new prediction.

## Output boundary

Predictions are stored only at `ai/quarantine/predictions/tokyo-20261107-09-top3.csv`, with provenance and input hashes beside them. Do not copy these files into `public/`, `ai/published/`, a Next.js API route, Vercel, or any external service.
