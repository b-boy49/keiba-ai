"""Offline CSV watcher for the target race; deliberately has no network client."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from .rights import sha256_file, verify_dataset_purpose
from .target_intake import history_coverage_report, predict_target_research
from .target_race import TARGET_RACE

REQUIRED = {"entries": "entries.csv", "performances": "post-2025-results.csv", "horses": "horses.csv", "jockeys": "jockeys.csv"}


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _status(output_dir: Path, state: str, **extra: object) -> dict:
    result = {"schema_version": 1, "visibility": "LOCAL_INTERNAL_ONLY", "target_race": TARGET_RACE["race_id"], "state": state, "checked_at": datetime.now(timezone.utc).isoformat(), **extra}
    _write_json(output_dir / "target-prediction-status.json", result)
    return result


def _inputs(directory: Path) -> tuple[dict[str, Path] | None, list[str]]:
    paths = {kind: directory / filename for kind, filename in REQUIRED.items()}
    missing = [filename for kind, filename in REQUIRED.items() if not paths[kind].is_file()]
    return (None, missing) if missing else (paths, [])


def _card_state(entries: pd.DataFrame) -> str:
    target = entries.loc[entries["race_id"].astype(str).eq(TARGET_RACE["race_id"])].copy()
    if target.empty:
        return "ENTRY_WAITING"
    if not target["entry_status"].eq("CONFIRMED").all():
        return "ENTRY_WAITING"
    numeric = pd.to_numeric(target.get("gate_no"), errors="coerce")
    numbers = pd.to_numeric(target.get("horse_no"), errors="coerce")
    if numeric.isna().any() or numbers.isna().any() or (numeric <= 0).any() or (numbers <= 0).any():
        return "GATE_WAITING"
    return "CONFIRMED"


def run_target_watch(*, intake_dir: str | Path, output_dir: str | Path, model_dir: str | Path, registry_path: str | Path, feature_as_of: str) -> dict:
    """Check approved CSV arrival, then predict once per unique input fingerprint.

    This function never downloads a card or result. An authorized operator must
    first import the CSVs with the existing rights-checked commands.
    """
    intake, output = Path(intake_dir), Path(output_dir)
    if Path("ai/quarantine").resolve() not in output.resolve().parents:
        raise PermissionError("Watcher output must remain under ai/quarantine")
    files, missing = _inputs(intake)
    if missing:
        return _status(output, "DATA_WAITING", missing_files=missing)
    assert files is not None
    try:
        for path in files.values():
            verify_dataset_purpose(path, "internal_storage")
        entries = pd.read_csv(files["entries"])
        card = _card_state(entries)
        manifest = {kind: {"path": str(path), "sha256": sha256_file(path)} for kind, path in files.items()}
        _write_json(output / "target-input-manifest.json", {"target_race": TARGET_RACE["race_id"], "checked_at": datetime.now(timezone.utc).isoformat(), "inputs": manifest})
        if card != "CONFIRMED":
            return _status(output, card, input_manifest=manifest)
        coverage = output / "target-history-coverage.csv"
        history_coverage_report(files["entries"], files["performances"], coverage, feature_as_of)
        gaps = pd.read_csv(coverage)
        if gaps["history_status"].ne("SUFFICIENT").any():
            return _status(output, "DATA_INSUFFICIENT", input_manifest=manifest, coverage_report=str(coverage), insufficient_horses=int(gaps["history_status"].ne("SUFFICIENT").sum()))
        fingerprint = sha256_file(files["entries"]) + sha256_file(files["performances"]) + sha256_file(files["horses"]) + sha256_file(files["jockeys"])
        state_path = output / "target-watch-state.json"
        previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        prediction = output / "tokyo-20261107-09-top3.csv"
        if previous.get("fingerprint") == fingerprint and prediction.exists():
            return _status(output, "PREDICTION_CURRENT", input_manifest=manifest, prediction=str(prediction))
        predict_target_research(entries_path=files["entries"], performances_path=files["performances"], horses_path=files["horses"], jockeys_path=files["jockeys"], model_dir=model_dir, registry_path=registry_path, output_path=prediction, feature_as_of=feature_as_of)
        _write_json(state_path, {"fingerprint": fingerprint, "predicted_at": datetime.now(timezone.utc).isoformat(), "prediction": str(prediction)})
        return _status(output, "PREDICTION_COMPLETE", input_manifest=manifest, prediction=str(prediction))
    except Exception as error:
        return _status(output, "PROCESSING_FAILED", error_type=type(error).__name__, message=str(error))
