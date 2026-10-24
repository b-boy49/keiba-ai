"""The sole presentation target. No network access and no fabricated entries."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import pandas as pd

TARGET_RACE = {"race_id": "tokyo-20261107-09", "race_date": "2026-11-07", "course_id": "tokyo", "race_no": 9, "race_name": "神奈川新聞杯", "surface": "DIRT", "distance_m": 2100, "class_name": "3歳以上2勝クラス・定量", "scheduled_start": "14:25", "schedule_source": "https://www.jra.go.jp/keiba/calendar2026/2026/11/1107.html"}

def _mean_or_nan(frame: pd.DataFrame) -> float:
    return float(frame["finish_position"].mean()) if len(frame) else float("nan")

def build_target_features(entries_path: str | Path, performances_path: str | Path, output_path: str | Path, feature_as_of: str) -> Path:
    """Build only pre-race aggregate features for confirmed target entries."""
    entries, past = pd.read_csv(entries_path), pd.read_csv(performances_path)
    required_entries = {"race_id", "horse_id", "horse_name", "jockey_id", "entry_status"}; required_past = {"horse_id", "jockey_id", "race_date", "course_id", "surface", "distance_m", "finish_position"}
    if required_entries - set(entries.columns) or required_past - set(past.columns): raise ValueError("対象レースの出走馬CSVまたは過去成績CSVの必須列が不足しています")
    target_entries = entries.loc[entries["race_id"].astype(str) == TARGET_RACE["race_id"]].copy()
    if target_entries.empty: raise ValueError("対象レースの出走馬CSVがありません")
    if not target_entries["entry_status"].eq("CONFIRMED").all(): raise ValueError("出走馬・騎手が確定していないため特徴量を生成できません")
    as_of = pd.to_datetime(feature_as_of, utc=True, errors="raise"); target_day = pd.Timestamp(TARGET_RACE["race_date"], tz="UTC")
    if as_of > target_day: raise ValueError("予測時点が対象レース後です")
    past = past.copy(); past["race_date"] = pd.to_datetime(past["race_date"], utc=True, errors="raise")
    if (past["race_date"] > as_of).any(): raise ValueError("予測時点より後の過去成績が混入しています")
    if (past["race_date"] >= target_day).any(): raise ValueError("対象レース当日以後の成績は使えません")
    rows = []
    for entry in target_entries.itertuples(index=False):
        horse = past.loc[past["horse_id"].astype(str) == str(entry.horse_id)].sort_values("race_date", ascending=False); recent = horse.head(3)
        distance = horse.loc[(horse["surface"] == "DIRT") & (pd.to_numeric(horse["distance_m"]) == 2100)]
        tokyo = horse.loc[horse["course_id"] == "tokyo"]; pairing = horse.loc[horse["jockey_id"].astype(str) == str(entry.jockey_id)]
        jockey = past.loc[past["jockey_id"].astype(str) == str(entry.jockey_id)]
        last_date = horse["race_date"].max() if len(horse) else pd.NaT
        rows.append({"race_id": TARGET_RACE["race_id"], "race_date": TARGET_RACE["race_date"], "feature_as_of": as_of.isoformat(), "horse_id": entry.horse_id, "horse_name": entry.horse_name, "jockey_id": entry.jockey_id, "surface": "DIRT", "distance_m": 2100, "track_condition": "UNKNOWN", "place_id": "05", "gate_number": getattr(entry, "gate_no", getattr(entry, "gate_number", 0)), "horse_number": getattr(entry, "horse_no", getattr(entry, "horse_number", 0)), "carried_weight_kg": getattr(entry, "carried_weight_kg", 0.0), "field_size": len(target_entries), "recent_finish_avg": _mean_or_nan(recent), "recent3_finish_avg": _mean_or_nan(recent), "distance_experience": len(distance), "jockey_win_rate": float((jockey["finish_position"] == 1).mean()) if len(jockey) else float("nan"), "jockey_top3_rate": float((jockey["finish_position"] <= 3).mean()) if len(jockey) else float("nan"), "days_since_last_run": int((as_of - last_date).days) if pd.notna(last_date) else float("nan"), "dirt_2100_finish_avg": _mean_or_nan(distance), "tokyo_starts": len(tokyo), "tokyo_finish_avg": _mean_or_nan(tokyo), "current_course_starts": len(tokyo), "current_course_finish_avg": _mean_or_nan(tokyo), "recent5_win_rate": float((recent["finish_position"] == 1).mean()) if len(recent) else 0.0, "recent5_top3_rate": float((recent["finish_position"] <= 3).mean()) if len(recent) else 0.0, "jockey_horse_starts": len(pairing), "jockey_horse_finish_avg": _mean_or_nan(pairing), "data_source": "registered-target-csv", "is_synthetic": False})
    target = Path(output_path); target.parent.mkdir(parents=True, exist_ok=True); pd.DataFrame(rows).to_csv(target, index=False)
    target.with_suffix(target.suffix + ".target.json").write_text(json.dumps({"target_race": TARGET_RACE, "feature_as_of": as_of.isoformat(), "entries": len(rows), "created_at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
