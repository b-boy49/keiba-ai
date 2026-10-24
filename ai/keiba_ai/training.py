from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from .features import align_feature_columns, build_feature_frame, build_research_feature_frame

@dataclass
class Metrics:
    brier: float; log_loss: float; winner_top1_accuracy: float; winner_top3_recall: float; rows: int; races: int

def split_by_race_date(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = sorted(frame["race_date"].dt.normalize().unique())
    if len(dates) < 12: raise ValueError("時系列分割には少なくとも12開催日が必要です")
    train_end = max(1, int(len(dates) * .60)); validation_end = max(train_end + 1, int(len(dates) * .80))
    train_dates, validation_dates, test_dates = set(dates[:train_end]), set(dates[train_end:validation_end]), set(dates[validation_end:])
    return frame[frame["race_date"].dt.normalize().isin(train_dates)].copy(), frame[frame["race_date"].dt.normalize().isin(validation_dates)].copy(), frame[frame["race_date"].dt.normalize().isin(test_dates)].copy()

def normalized_race_scores(frame: pd.DataFrame, probabilities: np.ndarray) -> np.ndarray:
    values = pd.Series(probabilities, index=frame.index).clip(lower=1e-6)
    return (values / values.groupby(frame["race_id"]).transform("sum")).to_numpy()

def evaluate_scores(frame: pd.DataFrame, scores: np.ndarray) -> Metrics:
    y = (frame["finish_position"] == 1).astype(int).to_numpy(); safe = np.clip(scores, 1e-6, 1 - 1e-6)
    ranked = frame.assign(_score=scores).sort_values(["race_id", "_score"], ascending=[True, False]); winners = ranked.groupby("race_id", sort=False).head(1)
    top3 = ranked.groupby("race_id", sort=False).head(3)
    return Metrics(brier=float(brier_score_loss(y, safe)), log_loss=float(log_loss(y, safe, labels=[0, 1])), winner_top1_accuracy=float((winners["finish_position"] == 1).mean()), winner_top3_recall=float((top3["finish_position"] == 1).sum() / frame["race_id"].nunique()), rows=len(frame), races=frame["race_id"].nunique())

def train_candidate(frame: pd.DataFrame, artifacts_root: str | Path = "ai/artifacts") -> tuple[Path, Metrics]:
    train, validation, test = split_by_race_date(frame); x_train, y_train = build_feature_frame(train); x_val, y_val = build_feature_frame(validation); x_test, _ = build_feature_frame(test)
    x_val = align_feature_columns(x_val, list(x_train.columns)); x_test = align_feature_columns(x_test, list(x_train.columns))
    model = LGBMClassifier(n_estimators=160, learning_rate=.05, num_leaves=15, min_child_samples=12, subsample=.85, colsample_bytree=.9, random_state=42, verbosity=-1)
    model.fit(x_train, y_train)
    validation_raw = model.predict_proba(x_val)[:, 1]
    calibrator = LogisticRegression(random_state=42).fit(validation_raw.reshape(-1, 1), y_val)
    test_raw = model.predict_proba(x_test)[:, 1]; test_calibrated = calibrator.predict_proba(test_raw.reshape(-1, 1))[:, 1]; test_scores = normalized_race_scores(test, test_calibrated); metrics = evaluate_scores(test, test_scores)
    version = datetime.now(timezone.utc).strftime("candidate-%Y%m%dT%H%M%SZ"); directory = Path(artifacts_root) / version; directory.mkdir(parents=True, exist_ok=False)
    provenance = frame.attrs.get("provenance")
    metadata = {"version": version, "trained_at": datetime.now(timezone.utc).isoformat(), "data_source": sorted(frame.get("data_source", pd.Series(["unknown"])).astype(str).unique().tolist()), "contains_synthetic": bool(frame.get("is_synthetic", pd.Series([False])).astype(bool).any()), "rights_verified": provenance is not None, "dataset_provenance": provenance, "dataset_races": int(frame["race_id"].nunique()), "split": {"train_max": str(train["race_date"].max()), "validation_max": str(validation["race_date"].max()), "test_min": str(test["race_date"].min())}, "metrics": asdict(metrics), "calibration_status": "holdout_measured_reference_score", "probability_policy": "calibrated reference score only; not a validated public win probability", "approval": "candidate_only"}
    joblib.dump({"model": model, "calibrator": calibrator, "feature_columns": list(x_train.columns), "metadata": metadata}, directory / "model.joblib")
    (directory / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return directory, metrics

def load_bundle(model_dir: str | Path): return joblib.load(Path(model_dir) / "model.joblib")

def predict(bundle: dict, frame: pd.DataFrame) -> pd.DataFrame:
    builder = build_research_feature_frame if bundle.get("metadata", {}).get("feature_builder") == "research_all_dirt" else build_feature_frame
    features, _ = builder(frame); features = align_feature_columns(features, bundle["feature_columns"]); raw = bundle["model"].predict_proba(features)[:, 1]; calibrated = bundle["calibrator"].predict_proba(raw.reshape(-1, 1))[:, 1]; scores = normalized_race_scores(frame, calibrated)
    output = frame[["race_id", "race_date", "horse_id", "horse_name"]].copy(); output["reference_win_score"] = scores; output["predicted_rank"] = output.groupby("race_id")["reference_win_score"].rank(method="first", ascending=False).astype(int); output["model_version"] = bundle["metadata"]["version"]; output["is_synthetic"] = frame.get("is_synthetic", False); output["feature_snapshot_at"] = frame.get("feature_as_of", ""); output["analysis_basis"] = "ダート2100m適性・東京実績・近走成績・騎手との組み合わせ（予測時点までの登録情報）"; output["prediction_label"] = "参考スコア（検証中・実競馬予想ではありません）"; return output.sort_values(["race_id", "predicted_rank"])
