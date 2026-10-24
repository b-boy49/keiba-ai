"""Canonical Phase 6A CSV schemas.  Import is rejected on missing/extra-invalid data."""
from __future__ import annotations

import pandas as pd

ENTRY_STATUSES = {"CONFIRMED", "CANCELLED", "SCRATCHED"}

ENTITY_SCHEMAS: dict[str, set[str]] = {
    "races": {"race_id", "race_date", "course_id", "race_no", "race_name", "scheduled_start", "surface", "distance_m", "status"},
    "entries": {"race_id", "horse_id", "horse_name", "jockey_id", "jockey_name", "entry_status", "gate_no", "horse_no", "carried_weight_kg", "published_at"},
    "past_performances": {"race_id", "horse_id", "jockey_id", "race_date", "course_id", "finish_position", "surface", "distance_m", "track_condition"},
    "horses": {"horse_id", "horse_name"}, "jockeys": {"jockey_id", "jockey_name"},
    "results": {"race_id", "horse_id", "finish_position", "finalized_at"},
}

def validate_entity_frame(frame: pd.DataFrame, record_type: str) -> pd.DataFrame:
    required = ENTITY_SCHEMAS.get(record_type)
    if required is None: raise ValueError("CSVデータ種別が未定義です")
    missing = required - set(frame.columns)
    if missing: raise ValueError(f"{record_type} CSVに必要な列がありません: {', '.join(sorted(missing))}")
    if frame.empty: raise ValueError("CSVにデータ行がありません")
    if frame[list(required)].isna().any().any(): raise ValueError("必須列に欠損があります")
    if record_type in {"races", "past_performances"}: pd.to_datetime(frame["race_date"], errors="raise")
    if record_type in {"entries", "results"}: pd.to_datetime(frame["published_at" if record_type == "entries" else "finalized_at"], utc=True, errors="raise")
    if record_type == "entries":
        status = frame["entry_status"].astype(str).str.upper()
        if not status.isin(ENTRY_STATUSES).all():
            raise ValueError(f"entry_status must be one of: {', '.join(sorted(ENTRY_STATUSES))}")
        for field, low, high in (("gate_no", 1, 8), ("horse_no", 1, 18)):
            values = pd.to_numeric(frame[field], errors="raise")
            if ((values < low) | (values > high) | (values % 1 != 0)).any():
                raise ValueError(f"{field} must be an integer from {low} to {high}")
        weight = pd.to_numeric(frame["carried_weight_kg"], errors="raise")
        if ((weight < 40.0) | (weight > 70.0)).any():
            raise ValueError("carried_weight_kg must be between 40.0 and 70.0")
        if frame[["horse_name", "jockey_name"]].astype(str).apply(lambda c: c.str.strip().eq("")).any().any():
            raise ValueError("horse_name and jockey_name must not be blank")
    if "distance_m" in frame and ((pd.to_numeric(frame["distance_m"], errors="raise") <= 0) | (pd.to_numeric(frame["distance_m"], errors="raise") > 10000)).any(): raise ValueError("distance_m が異常値です")
    if "race_no" in frame and ((pd.to_numeric(frame["race_no"], errors="raise") < 1) | (pd.to_numeric(frame["race_no"], errors="raise") > 24)).any(): raise ValueError("race_no が異常値です")
    if "finish_position" in frame and (pd.to_numeric(frame["finish_position"], errors="raise") <= 0).any(): raise ValueError("finish_position は正の整数である必要があります")
    keys = {"races": ["race_id"], "entries": ["race_id", "horse_id"], "past_performances": ["race_id", "horse_id"], "horses": ["horse_id"], "jockeys": ["jockey_id"], "results": ["race_id", "horse_id"]}[record_type]
    if frame.duplicated(keys).any(): raise ValueError("一意キーが重複しています")
    return frame.copy()
