"""Fail-closed intake and internal-only prediction for the 2026 target race."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from .csv_schemas import validate_entity_frame
from .data import import_entity_csv
from .rights import verify_dataset_purpose, write_prediction_provenance
from .target_race import TARGET_RACE, build_target_features
from .training import load_bundle, predict

POST_2025_START = pd.Timestamp("2025-03-01", tz="UTC")


def _read_entities(path: str | Path, kind: str) -> pd.DataFrame:
    frame = validate_entity_frame(pd.read_csv(path), kind)
    return frame.assign(**{c: frame[c].astype(str).str.strip() for c in ("horse_id", "horse_name", "jockey_id", "jockey_name") if c in frame})


def validate_target_identities(entries_path: str | Path, horses_path: str | Path, jockeys_path: str | Path) -> pd.DataFrame:
    """Ensure target entries use one canonical ID/name pair across old and new data."""
    entries = _read_entities(entries_path, "entries")
    horses = _read_entities(horses_path, "horses")
    jockeys = _read_entities(jockeys_path, "jockeys")
    if horses["horse_name"].duplicated().any() or jockeys["jockey_name"].duplicated().any():
        raise ValueError("Identity lookup has ambiguous duplicate horse or jockey names; resolve aliases before import")
    horse_names = horses.set_index("horse_id")["horse_name"]
    jockey_names = jockeys.set_index("jockey_id")["jockey_name"]
    for row in entries.itertuples(index=False):
        if horse_names.get(row.horse_id) != row.horse_name:
            raise ValueError(f"horse ID/name mismatch: {row.horse_id} / {row.horse_name}")
        if jockey_names.get(row.jockey_id) != row.jockey_name:
            raise ValueError(f"jockey ID/name mismatch: {row.jockey_id} / {row.jockey_name}")
    return entries


def _validate_history_ids(frame: pd.DataFrame, horses_path: str | Path, jockeys_path: str | Path) -> None:
    """Reject a period-specific source ID that is absent from the canonical maps."""
    horses = _read_entities(horses_path, "horses")
    jockeys = _read_entities(jockeys_path, "jockeys")
    unknown_horses = set(frame["horse_id"].astype(str)) - set(horses["horse_id"])
    unknown_jockeys = set(frame["jockey_id"].astype(str)) - set(jockeys["jockey_id"])
    if unknown_horses or unknown_jockeys:
        raise ValueError("Historical CSV contains IDs absent from the canonical horse/jockey lookup; add reviewed cross-period mappings first")


def import_post_2025_results(input_path: str | Path, output_path: str | Path, *, horses_path: str | Path, jockeys_path: str | Path, provider_id: str, rights_manifest: str | Path) -> Path:
    """Import only results dated 2025-03-01 onward through the rights-checked path."""
    frame = _read_entities(input_path, "past_performances")
    dates = pd.to_datetime(frame["race_date"], utc=True, errors="raise")
    if (dates < POST_2025_START).any():
        raise ValueError("This intake accepts race_date on or after 2025-03-01 only")
    _validate_history_ids(frame, horses_path, jockeys_path)
    staged = Path(output_path).with_suffix(".source.csv")
    staged.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(staged, index=False)
    try:
        return import_entity_csv(staged, output_path, record_type="past_performances", rights_manifest=rights_manifest, provider_id=provider_id)
    finally:
        staged.unlink(missing_ok=True)


def history_coverage_report(entries_path: str | Path, performances_path: str | Path, output_path: str | Path, feature_as_of: str) -> Path:
    entries = pd.read_csv(entries_path)
    past = pd.read_csv(performances_path)
    as_of = pd.to_datetime(feature_as_of, utc=True, errors="raise")
    dates = pd.to_datetime(past["race_date"], utc=True, errors="raise")
    usable = past.loc[dates <= as_of].copy(); usable["race_date"] = dates.loc[dates <= as_of]
    rows = []
    for entry in entries.loc[entries["race_id"].astype(str).eq(TARGET_RACE["race_id"])].itertuples(index=False):
        horse = usable.loc[usable["horse_id"].astype(str).eq(str(entry.horse_id))]
        latest = horse["race_date"].max() if not horse.empty else pd.NaT
        reasons = []
        if horse.empty: reasons.append("no_prior_performance")
        if pd.notna(latest) and latest < POST_2025_START: reasons.append("no_result_since_2025_03_01")
        rows.append({"race_id": TARGET_RACE["race_id"], "horse_id": entry.horse_id, "horse_name": entry.horse_name,
                     "prior_starts": len(horse), "latest_prior_race_date": latest.isoformat() if pd.notna(latest) else "",
                     "history_status": "SUFFICIENT" if not reasons else "INSUFFICIENT", "missing_reason": ";".join(reasons),
                     "model_missing_value_policy": "LightGBM accepts NaN for unavailable aggregate features; no missing value is replaced with zero",
                     "inference_eligibility": "MODEL_CAN_HANDLE_HISTORY_GAP" if reasons else "READY",
                     "identity_requirement": "canonical horse and jockey IDs must be reviewed before inference"})
    target = Path(output_path); target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(target, index=False)
    return target


def predict_target_research(*, entries_path: str | Path, performances_path: str | Path, horses_path: str | Path, jockeys_path: str | Path, model_dir: str | Path, registry_path: str | Path, output_path: str | Path, feature_as_of: str) -> Path:
    """Produce a Top-3 internal report. It cannot write outside ai/quarantine."""
    output = Path(output_path).resolve(); quarantine = Path("ai/quarantine").resolve()
    if quarantine not in output.parents:
        raise PermissionError("Research predictions must be written under ai/quarantine")
    for dataset in (entries_path, performances_path, horses_path, jockeys_path):
        verify_dataset_purpose(dataset, "internal_storage")
    entries = validate_target_identities(entries_path, horses_path, jockeys_path)
    _validate_history_ids(pd.read_csv(performances_path), horses_path, jockeys_path)
    if not entries.loc[entries["race_id"].astype(str).eq(TARGET_RACE["race_id"]), "entry_status"].eq("CONFIRMED").all():
        raise ValueError("Confirmed entry table is required; no prediction is produced for provisional entries")
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    model = Path(model_dir).resolve()
    if not registry.get("approved_manually") or Path(registry.get("active_model", "")).resolve() != model:
        raise PermissionError("Requested research model is not the manually approved active internal model")
    if quarantine not in model.parents:
        raise PermissionError("Only a quarantined research model may be used here")
    feature_path = output.with_suffix(".features.csv")
    build_target_features(entries_path, performances_path, feature_path, feature_as_of)
    frame = pd.read_csv(feature_path)
    result = predict(load_bundle(model), frame).copy()
    # Keep every confirmed runner. Scores are model output only; deterministic
    # horse-ID tie breaking prevents an arbitrary presentation order.
    result = result.sort_values(["reference_win_score", "horse_id"], ascending=[False, True], kind="stable").reset_index(drop=True)
    result["predicted_rank"] = result.index + 1
    result["visibility"] = "INTERNAL_RESEARCH_ONLY"
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    output.parent.mkdir(parents=True, exist_ok=True); result.to_csv(output, index=False)
    write_prediction_provenance(output, model_version=load_bundle(model)["metadata"]["version"], training_provenance=load_bundle(model)["metadata"].get("dataset_provenance"))
    return output
