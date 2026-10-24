"""Internal-only all-dirt experiments evaluated on held-out Tokyo dirt 2100m.

No function in this module is used by a web route or publication command.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression

from .features import align_feature_columns, build_research_feature_frame
from .training import evaluate_scores, normalized_race_scores


def _target(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[(frame["surface"].astype(str) == "DIRT") & (frame["distance_m"] == 2100) & (frame.get("place_id", "") .astype(str).str.zfill(2) == "05")].copy()


def _splits(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    target = _target(frame)
    dates = sorted(target["race_date"].dt.normalize().unique())
    if len(dates) < 12:
        raise ValueError("At least 12 Tokyo dirt 2100m race dates are required")
    train_end = max(1, int(len(dates) * .60)); validation_end = max(train_end + 1, int(len(dates) * .80))
    train_end_date, validation_end_date = dates[train_end - 1], dates[validation_end - 1]
    # All dirt races may expand only the training period.  Validation and test
    # metrics always remain the same target cohort and held-out dates.
    train_all = frame.loc[frame["race_date"].dt.normalize() <= train_end_date].copy()
    validation = target.loc[(target["race_date"].dt.normalize() > train_end_date) & (target["race_date"].dt.normalize() <= validation_end_date)].copy()
    test = target.loc[target["race_date"].dt.normalize() > validation_end_date].copy()
    return train_all, validation, test, target


def _score(model: LGBMClassifier, calibrator: LogisticRegression, frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    x, _ = build_research_feature_frame(frame)
    raw = model.predict_proba(align_feature_columns(x, columns))[:, 1]
    return normalized_race_scores(frame, calibrator.predict_proba(raw.reshape(-1, 1))[:, 1])


def _history_scores(frame: pd.DataFrame) -> np.ndarray:
    recent = pd.to_numeric(frame["recent_finish_avg"], errors="coerce").replace(0, np.nan).fillna(99.0)
    return normalized_race_scores(frame, (1.0 / recent).to_numpy())


def run_all_dirt_research(input_path: str | Path, output_root: str | Path) -> Path:
    """Tune only on validation, then report one untouched Tokyo-2100 test result."""
    from .data import load_authorized_training_csv
    frame = load_authorized_training_csv(input_path)
    frame["race_date"] = pd.to_datetime(frame["race_date"], utc=True, errors="raise")
    train, validation, test, target = _splits(frame)
    x_train, y_train = build_research_feature_frame(train)
    x_val, y_val = build_research_feature_frame(validation)
    x_val = align_feature_columns(x_val, list(x_train.columns))
    configs = [
        {"name": "conservative", "n_estimators": 180, "learning_rate": .035, "num_leaves": 12, "min_child_samples": 35, "subsample": .9, "colsample_bytree": .85},
        {"name": "balanced", "n_estimators": 260, "learning_rate": .03, "num_leaves": 20, "min_child_samples": 28, "subsample": .9, "colsample_bytree": .9},
        {"name": "capacity", "n_estimators": 220, "learning_rate": .04, "num_leaves": 28, "min_child_samples": 45, "subsample": .85, "colsample_bytree": .95},
    ]
    trials = []
    for config in configs:
        params = {k: v for k, v in config.items() if k != "name"}
        model = LGBMClassifier(**params, random_state=42, verbosity=-1)
        model.fit(x_train, y_train)
        raw = model.predict_proba(x_val)[:, 1]
        calibrator = LogisticRegression(random_state=42, C=1.0).fit(raw.reshape(-1, 1), y_val)
        metrics = asdict(evaluate_scores(validation, normalized_race_scores(validation, calibrator.predict_proba(raw.reshape(-1, 1))[:, 1])))
        trials.append({"config": config, "validation_metrics": metrics, "model": model, "calibrator": calibrator})
    # A fixed validation-only selection rule: maximise winner Top1, then Top3,
    # then minimise log loss.  Test rows are never read during this selection.
    chosen = sorted(trials, key=lambda item: (-item["validation_metrics"]["winner_top1_accuracy"], -item["validation_metrics"]["winner_top3_recall"], item["validation_metrics"]["log_loss"]))[0]
    test_scores = _score(chosen["model"], chosen["calibrator"], test, list(x_train.columns))
    test_metrics = asdict(evaluate_scores(test, test_scores))
    baseline_metrics = asdict(evaluate_scores(test, _history_scores(test)))
    root = Path(output_root); root.mkdir(parents=True, exist_ok=True)
    version = datetime.now(timezone.utc).strftime("all-dirt-research-%Y%m%dT%H%M%SZ")
    directory = root / version; directory.mkdir()
    provenance = frame.attrs.get("provenance")
    metadata = {"version": version, "visibility": "internal research only; never publish", "approval": "candidate_only", "contains_synthetic": False, "feature_builder": "research_all_dirt", "rights_verified": provenance is not None, "dataset_provenance": provenance, "training_scope": "dirt 1800-2200m races through target training cutoff", "evaluation_scope": "Tokyo dirt 2100m only, chronological untouched test", "dataset": {"all_dirt_rows": len(frame), "all_dirt_races": int(frame["race_id"].nunique()), "tokyo_dirt_2100_rows": len(target), "tokyo_dirt_2100_races": int(target["race_id"].nunique())}, "split": {"train_max": str(train["race_date"].max()), "validation": [str(validation["race_date"].min()), str(validation["race_date"].max())], "test": [str(test["race_date"].min()), str(test["race_date"].max())]}, "features": list(x_train.columns), "selection": {"rule": "validation Top1, then Top3, then log loss", "trials": [{"config": item["config"], "validation_metrics": item["validation_metrics"]} for item in trials], "selected": chosen["config"]}, "test_metrics": {"model": test_metrics, "recent_finish_baseline": baseline_metrics}}
    joblib.dump({"model": chosen["model"], "calibrator": chosen["calibrator"], "feature_columns": list(x_train.columns), "metadata": metadata}, directory / "model.joblib")
    (directory / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return directory
