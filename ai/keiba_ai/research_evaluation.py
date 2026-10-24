"""Non-public benchmark and prediction-vs-result reporting for research models."""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .features import align_feature_columns, build_feature_frame
from .data import load_authorized_training_csv
from .training import evaluate_scores, load_bundle, normalized_race_scores, split_by_race_date


def _metrics(frame: pd.DataFrame, scores: np.ndarray) -> dict[str, float | int]:
    return asdict(evaluate_scores(frame, scores))


def _simple_history_scores(frame: pd.DataFrame) -> np.ndarray:
    # No-result history is not assumed favorable: unknown form is assigned a poor
    # fallback rank instead of treating a zero-filled feature as a win signal.
    recent = pd.to_numeric(frame["recent_finish_avg"], errors="raise").replace(0, np.nan).fillna(99.0)
    return normalized_race_scores(frame, (1.0 / recent).to_numpy())


def _model_scores(bundle: dict, frame: pd.DataFrame) -> np.ndarray:
    features, _ = build_feature_frame(frame)
    features = align_feature_columns(features, bundle["feature_columns"])
    raw = bundle["model"].predict_proba(features)[:, 1]
    calibrated = bundle["calibrator"].predict_proba(raw.reshape(-1, 1))[:, 1]
    return normalized_race_scores(frame, calibrated)


def _period(frame: pd.DataFrame) -> dict[str, object]:
    return {"rows": len(frame), "races": int(frame["race_id"].nunique()), "start": str(frame["race_date"].min()), "end": str(frame["race_date"].max())}


def _records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, object]]:
    selected = frame[columns].astype(object)
    return selected.where(pd.notna(selected), None).to_dict("records")


def generate_research_evaluation(input_path: str | Path, model_dir: str | Path, output_path: str | Path, *, random_trials: int = 200) -> Path:
    """Write an internal-only JSON report; it has no web/publication integration."""
    # An internal report is still derived from rights-tracked data.  Refuse a
    # bare CSV so this command cannot become a route around provenance checks.
    frame = load_authorized_training_csv(input_path)
    frame["race_date"] = pd.to_datetime(frame["race_date"], utc=True, errors="raise")
    train, validation, test = split_by_race_date(frame)
    bundle = load_bundle(model_dir)
    model_scores = _model_scores(bundle, test)
    history_scores = _simple_history_scores(test)
    rng = np.random.default_rng(20261023)
    random_metrics = [_metrics(test, normalized_race_scores(test, rng.random(len(test)))) for _ in range(random_trials)]
    metric_names = ["brier", "log_loss", "winner_top1_accuracy", "winner_top3_recall"]
    random_summary = {name: {"mean": float(np.mean([item[name] for item in random_metrics])), "std": float(np.std([item[name] for item in random_metrics], ddof=1))} for name in metric_names}
    ranked = test[["race_id", "race_date", "horse_id", "horse_name", "finish_position", "recent_finish_avg", "dirt_2100_finish_avg", "tokyo_starts", "jockey_win_rate"]].copy()
    ranked["reference_win_score"] = model_scores
    ranked["predicted_rank"] = ranked.groupby("race_id")["reference_win_score"].rank(method="first", ascending=False).astype(int)
    examples = []
    for race_id, group in ranked.groupby("race_id", sort=True):
        top3 = group.sort_values("predicted_rank").head(3)
        winner = group.loc[group["finish_position"] == 1].head(1)
        examples.append({"race_id": str(race_id), "race_date": str(group["race_date"].iloc[0]), "actual_winner": _records(winner, ["horse_id", "horse_name", "finish_position"]), "model_top3": _records(top3, ["horse_id", "horse_name", "predicted_rank", "finish_position", "reference_win_score", "recent_finish_avg", "dirt_2100_finish_avg", "tokyo_starts", "jockey_win_rate"]), "reason_fields": ["recent_finish_avg", "dirt_2100_finish_avg", "tokyo_starts", "jockey_win_rate"]})
    report = {"schema_version": 1, "visibility": "internal research only; never publish or copy into web snapshots", "model": {"version": bundle["metadata"]["version"], "approval": bundle["metadata"].get("approval"), "publication_permitted": (bundle["metadata"].get("dataset_provenance") or {}).get("publication_permitted", False)}, "method": {"split": "chronological unique race dates: 60% train, 20% validation/calibration, 20% test", "same_day_leakage": "Race-day outcomes are applied after all races on that date.", "excluded_result_fields": ["finish_position", "time", "finalt", "time_factor"], "random_trials": random_trials}, "periods": {"train": _period(train), "validation": _period(validation), "test": _period(test)}, "features": list(bundle["feature_columns"]), "metrics": {"model": _metrics(test, model_scores), "simple_recent_finish_baseline": _metrics(test, history_scores), "random_uniform": random_summary}, "prediction_vs_actual": examples}
    target = Path(output_path); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return target
