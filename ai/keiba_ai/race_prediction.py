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


def _confirmed_runners(entries: pd.DataFrame, spec: dict) -> pd.DataFrame:
    """Return the declared field, without silently ranking withdrawals."""
    card = entries.loc[entries["race_id"].astype(str).eq(str(spec["race_id"]))].copy()
    if card.empty:
        raise ValueError("Race card has no rows for the configured race")
    allowed_statuses = {"CONFIRMED", "CANCELLED", "SCRATCHED"}
    statuses = set(card["entry_status"].astype(str))
    if not statuses <= allowed_statuses:
        raise ValueError("Race card contains an unsupported entry status")
    runners = card.loc[card["entry_status"].astype(str).eq("CONFIRMED")].copy()
    expected = spec.get("expected_confirmed_runners")
    if expected is not None and len(runners) != int(expected):
        raise ValueError(
            f"Configured race requires {int(expected)} confirmed runners; found {len(runners)}. "
            "No partial ranking is produced"
        )
    if runners.empty:
        raise ValueError("No confirmed runners are available for inference")
    if runners["horse_id"].duplicated().any() or runners["horse_no"].duplicated().any():
        raise ValueError("Race card contains duplicate confirmed horse ID or horse number")
    return runners


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
    runners = _confirmed_runners(entries, spec)
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


def race_history_coverage_report(*, spec_path: str | Path, entries_path: str | Path, performances_path: str | Path, output_path: str | Path, feature_as_of: str) -> Path:
    """Describe pre-race history gaps without treating them as invented values."""
    spec = load_race_spec(spec_path)
    entries, past = pd.read_csv(entries_path), pd.read_csv(performances_path)
    runners = _confirmed_runners(entries, spec)
    as_of, race_day = pd.to_datetime(feature_as_of, utc=True, errors="raise"), pd.Timestamp(spec["race_date"], tz="UTC")
    if as_of > race_day:
        raise ValueError("Feature-as-of time must not be after the race date")
    if "race_date" not in past:
        raise ValueError("Performance CSV is missing race_date")
    past = past.copy(); past["race_date"] = pd.to_datetime(past["race_date"], utc=True, errors="raise")
    if (past["race_date"] > as_of).any() or (past["race_date"] >= race_day).any():
        raise ValueError("Future or same-race-day performance is not permitted")
    rows: list[dict] = []
    for entry in runners.itertuples(index=False):
        horse = past.loc[past["horse_id"].astype(str).eq(str(entry.horse_id))]
        latest = horse["race_date"].max() if not horse.empty else pd.NaT
        rows.append({
            "race_id": spec["race_id"], "horse_id": entry.horse_id, "horse_name": entry.horse_name,
            "prior_starts": len(horse), "latest_prior_race_date": latest.isoformat() if pd.notna(latest) else "",
            "history_status": "AVAILABLE" if len(horse) else "MISSING",
            "missing_reason": "" if len(horse) else "no_pre_race_performance_in_approved_input",
            "model_missing_value_policy": "LightGBM accepts NaN for unavailable aggregate features; no missing value is replaced with zero",
            "inference_eligibility": "READY_WITH_AVAILABLE_HISTORY" if len(horse) else "MODEL_CAN_HANDLE_HISTORY_GAP",
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
    _confirmed_runners(entries, spec)
    registry, model = json.loads(Path(registry_path).read_text(encoding="utf-8")), Path(model_dir).resolve()
    if not registry.get("approved_manually") or Path(registry.get("active_model", "")).resolve() != model or quarantine not in model.parents:
        raise PermissionError("Only the manually approved active quarantined model may be used")
    features = build_race_features(spec_path=spec_path, entries_path=entries_path, performances_path=performances_path, output_path=output.with_suffix(".features.csv"), feature_as_of=feature_as_of)
    result = predict(load_bundle(model), pd.read_csv(features)).copy()
    result = result.sort_values(["reference_win_score", "horse_id"], ascending=[False, True], kind="stable").reset_index(drop=True)
    result["predicted_rank"] = result.index + 1
    result["visibility"] = "INTERNAL_RESEARCH_ONLY"; result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["validation_notice"] = (
        "Evaluation scope: chronological Tokyo dirt 2100m test."
        if str(spec["course_id"]).lower() == "tokyo" and int(spec["distance_m"]) == 2100
        else "Unvalidated condition: model metrics are Tokyo dirt 2100m only."
    )
    output.parent.mkdir(parents=True, exist_ok=True); result.to_csv(output, index=False)
    write_prediction_provenance(output, model_version=load_bundle(model)["metadata"]["version"], training_provenance=load_bundle(model)["metadata"].get("dataset_provenance"))
    return output
