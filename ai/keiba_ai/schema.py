from __future__ import annotations

REQUIRED_COLUMNS = {
    "race_id", "race_date", "horse_id", "horse_name", "jockey_id", "surface",
    "distance_m", "track_condition", "recent_finish_avg", "distance_experience",
    "jockey_win_rate", "days_since_last_run", "dirt_2100_finish_avg", "tokyo_starts",
    "tokyo_finish_avg", "jockey_horse_starts", "jockey_horse_finish_avg", "finish_position",
}
FEATURE_COLUMNS = [
    "surface", "distance_m", "track_condition", "recent_finish_avg",
    "distance_experience", "jockey_win_rate", "days_since_last_run", "dirt_2100_finish_avg",
    "tokyo_starts", "tokyo_finish_avg", "jockey_horse_starts", "jockey_horse_finish_avg",
]

# These fields are emitted by the quarantined all-dirt converter.  They are
# deliberately optional so that the original Tokyo 2100m baseline remains
# reproducible byte-for-byte in feature meaning.  Every field is known before
# the race; result, odds, and final-time fields are intentionally absent.
RESEARCH_EXTRA_FEATURE_COLUMNS = [
    "place_id", "gate_number", "horse_number", "carried_weight_kg", "field_size",
    "recent3_finish_avg", "jockey_top3_rate", "current_course_starts",
    "current_course_finish_avg", "recent5_win_rate", "recent5_top3_rate",
]

RESEARCH_CATEGORICAL_COLUMNS = ["surface", "track_condition", "place_id"]

def target_is_win(frame):
    return (frame["finish_position"] == 1).astype(int)
