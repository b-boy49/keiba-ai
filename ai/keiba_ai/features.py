from __future__ import annotations

import pandas as pd
from .schema import FEATURE_COLUMNS, RESEARCH_CATEGORICAL_COLUMNS, RESEARCH_EXTRA_FEATURE_COLUMNS, target_is_win

def build_feature_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Use only pre-race columns; finish_position is target-only and excluded."""
    data = frame.copy()
    features = data[FEATURE_COLUMNS].copy()
    features["distance_m"] = pd.to_numeric(features["distance_m"], errors="raise")
    for column in ["recent_finish_avg", "distance_experience", "jockey_win_rate", "days_since_last_run", "dirt_2100_finish_avg", "tokyo_starts", "tokyo_finish_avg", "jockey_horse_starts", "jockey_horse_finish_avg"]:
        features[column] = pd.to_numeric(features[column], errors="raise")
    features = pd.get_dummies(features, columns=["surface", "track_condition"], dtype=float)
    target = target_is_win(data) if "finish_position" in data.columns else pd.Series(index=data.index, dtype=int)
    return features, target

def align_feature_columns(features: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return features.reindex(columns=columns, fill_value=0.0)


def build_research_feature_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Build the richer all-dirt research feature set from pre-race columns.

    Missing optional fields are represented explicitly.  This keeps the
    baseline schema stable and prevents a source-dependent column from being
    silently mistaken for a result-derived feature.
    """
    columns = FEATURE_COLUMNS + RESEARCH_EXTRA_FEATURE_COLUMNS
    data = frame.copy()
    for column in columns:
        if column not in data:
            data[column] = "UNKNOWN" if column in RESEARCH_CATEGORICAL_COLUMNS else 0.0
    features = data[columns].copy()
    for column in columns:
        if column in RESEARCH_CATEGORICAL_COLUMNS:
            features[column] = features[column].fillna("UNKNOWN").astype(str)
        else:
            features[column] = pd.to_numeric(features[column], errors="coerce").fillna(0.0)
    features = pd.get_dummies(features, columns=RESEARCH_CATEGORICAL_COLUMNS, dtype=float)
    target = target_is_win(data) if "finish_position" in data.columns else pd.Series(index=data.index, dtype=int)
    return features, target
