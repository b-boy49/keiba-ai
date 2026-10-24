"""Explicit, offline publication of approved real-data AI snapshots.

This module deliberately has no network client.  A human runs it after model
approval; the web application only reads the resulting files.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd
from .rights import verify_dataset_purpose, verify_prediction_provenance, verify_provider_rights


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_approved_real_model(registry: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        active = _read_json(registry)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise ValueError("承認済みモデルのレジストリを確認できません") from error
    if active.get("approved_manually") is not True or not active.get("active_model"):
        raise ValueError("手動承認済みモデルがありません")
    metadata = _read_json(Path(active["active_model"]) / "metadata.json")
    if metadata.get("contains_synthetic"):
        raise ValueError("合成データを含むモデルは公開できません")
    if metadata.get("approval") != "approved":
        raise ValueError("候補モデルは公開できません。承認記録を確認してください")
    return active, metadata


def publish_prediction_snapshot(
    registry_path: str | Path,
    predictions_path: str | Path,
    race_id: str,
    source_name: str,
    rights_confirmed: bool,
    output_dir: str | Path = "ai/published",
    rights_manifest: str | Path | None = None,
    provider_id: str | None = None,
) -> Path:
    """Publish one race only after rights and model approval are explicit."""
    if not rights_confirmed:
        raise PermissionError("公開するデータの利用権限確認が必要です (--rights-confirmed)")
    active, metadata = _ensure_approved_real_model(Path(registry_path))
    if not rights_manifest or not provider_id: raise PermissionError("公開には提供元権利台帳と提供元IDが必要です")
    provider = verify_provider_rights(rights_manifest, provider_id, "training_features", {"public_display", "redistribution"})
    provenance = metadata.get("dataset_provenance") or {}
    if metadata.get("rights_verified") is not True or provenance.get("provider_id") != provider_id: raise PermissionError("モデルの学習データ来歴と公開提供元が一致しません")
    verify_prediction_provenance(predictions_path, metadata["version"], provider_id)
    predictions = pd.read_csv(predictions_path)
    required = {"race_id", "horse_id", "horse_name", "predicted_rank", "reference_win_score", "model_version", "feature_snapshot_at", "analysis_basis"}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"予測CSVに必要な列がありません: {sorted(missing)}")
    race_rows = predictions.loc[predictions["race_id"].astype(str) == str(race_id)].copy()
    if race_rows.empty:
        raise ValueError("指定レースの予測がありません")
    if "is_synthetic" in race_rows and race_rows["is_synthetic"].astype(bool).any():
        raise ValueError("合成予測は公開できません")
    if set(race_rows["model_version"].astype(str)) != {str(metadata["version"])}:
        raise ValueError("予測CSVのモデルバージョンが承認済みモデルと一致しません")

    published_at = datetime.now(timezone.utc).isoformat()
    items = [
        {"horse_id": str(row.horse_id), "horse_name": str(row.horse_name),
         "predicted_rank": int(row.predicted_rank), "reference_win_score": float(row.reference_win_score), "analysis_basis": str(row.analysis_basis)}
        for row in race_rows.sort_values("predicted_rank").itertuples(index=False)
    ]
    output = Path(output_dir)
    (output / "predictions").mkdir(parents=True, exist_ok=True)
    snapshot = {
        "schema_version": 1, "race_id": str(race_id), "published_at": published_at,
        "data_source": source_name or provider.get("name", provider_id), "model_version": metadata["version"],
        "trained_at": metadata.get("trained_at"), "approved_at": active.get("approved_at"), "feature_snapshot_at": str(race_rows["feature_snapshot_at"].iloc[0]),
        "probability_policy": metadata.get("probability_policy"), "predictions": items,
    }
    target = output / "predictions" / f"{race_id}.json"
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {"schema_version": 1, "published_at": published_at, "active_model": {"version": metadata["version"], "trained_at": metadata.get("trained_at"), "approved_at": active.get("approved_at"), "data_source": source_name or provider.get("name", provider_id), "contains_synthetic": False}}
    (output / "active-model.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def publish_performance_snapshot(
    predictions_path: str | Path, results_path: str | Path, source_name: str,
    rights_confirmed: bool, output_dir: str | Path = "ai/published",
    rights_manifest: str | Path | None = None, provider_id: str | None = None,
) -> Path:
    if not rights_confirmed:
        raise PermissionError("成績データの利用権限確認が必要です (--rights-confirmed)")
    if not rights_manifest or not provider_id: raise PermissionError("公開には提供元権利台帳と提供元IDが必要です")
    provider = verify_provider_rights(rights_manifest, provider_id, "results", {"public_display", "redistribution"})
    verify_dataset_purpose(results_path, "internal_storage")
    predictions, results = pd.read_csv(predictions_path), pd.read_csv(results_path)
    if "is_synthetic" in predictions and predictions["is_synthetic"].astype(bool).any():
        raise ValueError("合成予測の成績は公開できません")
    required_prediction, required_result = {"race_id", "horse_id", "predicted_rank"}, {"race_id", "horse_id", "finish_position"}
    if required_prediction - set(predictions.columns) or required_result - set(results.columns):
        raise ValueError("予測または結果CSVの必要列が不足しています")
    merged = predictions.merge(results[["race_id", "horse_id", "finish_position"]], on=["race_id", "horse_id"], how="inner")
    top = merged.sort_values(["race_id", "predicted_rank"]).groupby("race_id", as_index=False).first()
    races = int(top["race_id"].nunique())
    snapshot = {"schema_version": 1, "published_at": datetime.now(timezone.utc).isoformat(), "data_source": source_name or provider.get("name", provider_id), "races_evaluated": races, "top1_winner_hits": int((top["finish_position"] == 1).sum()), "top1_winner_rate": (float((top["finish_position"] == 1).mean()) if races else None)}
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True); target = output / "performance.json"
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
