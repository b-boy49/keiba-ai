"""Generic, local-only inference for an approved real race card.

Race-card and history inputs must already have provenance sidecars.  This
module has no HTTP client and has no public-output path.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from .rights import verify_dataset_purpose, write_prediction_provenance
from .target_intake import _validate_history_ids, validate_target_identities
from .training import load_bundle, predict


def load_race_spec(path: str | Path) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"race_id", "race_date", "course_id", "race_name", "race_no", "surface", "distance_m"}
    if missing := required - set(spec):
        raise ValueError(f"Race specification missing: {', '.join(sorted(missing))}")
    if str(spec["surface"]).upper() != "DIRT" or not 1800 <= int(spec["distance_m"]) <= 2200:
        raise ValueError("This research model accepts dirt races from 1800m through 2200m only")
    return spec


def _mean_or_nan(frame: pd.DataFrame) -> float:
    return float(frame["finish_position"].mean()) if len(frame) else float("nan")


def build_race_features(*, spec_path: str | Path, entries_path: str | Path, performances_path: str | Path, output_path: str | Path, feature_as_of: str) -> Path:
    """Build pre-race aggregates without replacing unavailable values by zero."""
    spec = load_race_spec(spec_path)
    entries, past = pd.read_csv(entries_path), pd.read_csv(performances_path)
    required_entries = {"race_id", "horse_id", "horse_name", "jockey_id", "entry_status"}
    required_past = {"horse_id", "jockey_id", "race_date", "course_id", "surface", "distance_m", "finish_position"}
    if required_entries - set(entries.columns) or required_past - set(past.columns):
        raise ValueError("Race-card or performance CSV is missing required columns")
    runners = entries.loc[entries["race_id"].astype(str).eq(str(spec["race_id"]))].copy()
    if runners.empty or not runners["entry_status"].eq("CONFIRMED").all():
        raise ValueError("A complete CONFIRMED race card is required before inference")
    if runners["horse_id"].duplicated().any() or runners["horse_no"].duplicated().any():
        raise ValueError("Race card contains duplicate horse ID or horse number")
    as_of, race_day = pd.to_datetime(feature_as_of, utc=True, errors="raise"), pd.Timestamp(spec["race_date"], tz="UTC")
    if as_of > race_day:
        raise ValueError("Feature-as-of time must not be after the race date")
    past = past.copy(); past["race_date"] = pd.to_datetime(past["race_date"], utc=True, errors="raise")
    if (past["race_date"] > as_of).any() or (past["race_date"] >= race_day).any():
        raise ValueError("Future or same-race-day performance is not permitted")
    rows: list[dict] = []
    for entry in runners.itertuples(index=False):
        horse = past.loc[past["horse_id"].astype(str).eq(str(entry.horse_id))].sort_values("race_date", ascending=False)
        recent = horse.head(3)
        distance = horse.loc[(horse["surface"].astype(str).eq("DIRT")) & (pd.to_numeric(horse["distance_m"]) == int(spec["distance_m"]))]
        course = horse.loc[horse["course_id"].astype(str).eq(str(spec["course_id"]))]
        pairing = horse.loc[horse["jockey_id"].astype(str).eq(str(entry.jockey_id))]
        jockey = past.loc[past["jockey_id"].astype(str).eq(str(entry.jockey_id))]
        last_date = horse["race_date"].max() if not horse.empty else pd.NaT
        rows.append({
            "race_id": spec["race_id"], "race_date": spec["race_date"], "feature_as_of": as_of.isoformat(),
            "horse_id": entry.horse_id, "horse_name": entry.horse_name, "jockey_id": entry.jockey_id,
            "surface": "DIRT", "distance_m": int(spec["distance_m"]), "track_condition": "UNKNOWN",
            "place_id": str(spec.get("place_id", "UNKNOWN")), "gate_number": getattr(entry, "gate_no", float("nan")),
            "horse_number": getattr(entry, "horse_no", float("nan")), "carried_weight_kg": getattr(entry, "carried_weight_kg", float("nan")),
            "field_size": len(runners), "recent_finish_avg": _mean_or_nan(recent), "recent3_finish_avg": _mean_or_nan(recent),
            "distance_experience": len(distance), "jockey_win_rate": float((jockey["finish_position"] == 1).mean()) if len(jockey) else float("nan"),
            "jockey_top3_rate": float((jockey["finish_position"] <= 3).mean()) if len(jockey) else float("nan"),
            "days_since_last_run": int((as_of - last_date).days) if pd.notna(last_date) else float("nan"),
            "dirt_2100_finish_avg": _mean_or_nan(distance) if int(spec["distance_m"]) == 2100 else float("nan"),
            "tokyo_starts": float("nan"), "tokyo_finish_avg": float("nan"), "current_course_starts": len(course),
            "current_course_finish_avg": _mean_or_nan(course), "recent5_win_rate": float((recent["finish_position"] == 1).mean()) if len(recent) else float("nan"),
            "recent5_top3_rate": float((recent["finish_position"] <= 3).mean()) if len(recent) else float("nan"),
            "jockey_horse_starts": len(pairing), "jockey_horse_finish_avg": _mean_or_nan(pairing),
            "data_source": "approved-race-card-and-history", "is_synthetic": False,
        })
    target = Path(output_path); target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(target, index=False)
    return target


def predict_configured_race_research(*, spec_path: str | Path, entries_path: str | Path, performances_path: str | Path, horses_path: str | Path, jockeys_path: str | Path, model_dir: str | Path, registry_path: str | Path, output_path: str | Path, feature_as_of: str) -> Path:
    """Run the manually approved quarantined model for every confirmed runner."""
    output, quarantine = Path(output_path).resolve(), Path("ai/quarantine").resolve()
    if quarantine not in output.parents:
        raise PermissionError("Research predictions must be written under ai/quarantine")
    for dataset in (entries_path, performances_path, horses_path, jockeys_path):
        verify_dataset_purpose(dataset, "internal_storage")
    entries = validate_target_identities(entries_path, horses_path, jockeys_path)
    _validate_history_ids(pd.read_csv(performances_path), horses_path, jockeys_path)
    spec = load_race_spec(spec_path)
    runners = entries.loc[entries["race_id"].astype(str).eq(str(spec["race_id"]))]
    if len(runners) != 10 or not runners["entry_status"].eq("CONFIRMED").all():
        raise ValueError("Niigata 8R demonstration requires all 10 confirmed runners; no partial ranking is produced")
    registry, model = json.loads(Path(registry_path).read_text(encoding="utf-8")), Path(model_dir).resolve()
    if not registry.get("approved_manually") or Path(registry.get("active_model", "")).resolve() != model or quarantine not in model.parents:
        raise PermissionError("Only the manually approved active quarantined model may be used")
    features = build_race_features(spec_path=spec_path, entries_path=entries_path, performances_path=performances_path, output_path=output.with_suffix(".features.csv"), feature_as_of=feature_as_of)
    result = predict(load_bundle(model), pd.read_csv(features)).copy()
    result = result.sort_values(["reference_win_score", "horse_id"], ascending=[False, True], kind="stable").reset_index(drop=True)
    result["predicted_rank"] = result.index + 1
    result["visibility"] = "INTERNAL_RESEARCH_ONLY"; result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["validation_notice"] = "Unvalidated condition: model metrics are Tokyo dirt 2100m only."
    output.parent.mkdir(parents=True, exist_ok=True); result.to_csv(output, index=False)
    write_prediction_provenance(output, model_version=load_bundle(model)["metadata"]["version"], training_provenance=load_bundle(model)["metadata"].get("dataset_provenance"))
    return output
