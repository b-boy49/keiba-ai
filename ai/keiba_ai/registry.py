from __future__ import annotations
from pathlib import Path
import json

def compare_candidates(candidate_metrics: dict, active_metrics: dict | None) -> dict:
    if active_metrics is None: return {"eligible_for_manual_approval": True, "reason": "初回候補。自動採用は禁止。手動承認が必要です。"}
    improved = candidate_metrics["brier"] < active_metrics["brier"] and candidate_metrics["winner_top1_accuracy"] >= active_metrics["winner_top1_accuracy"]
    return {"eligible_for_manual_approval": improved, "reason": "Brier score改善かつTop-1精度非悪化" if improved else "採用基準を満たしません。既存モデルを維持します。"}

def approve_candidate(candidate_dir: str | Path, registry_path: str | Path = "ai/artifacts/active.json") -> Path:
    candidate = Path(candidate_dir); metadata = json.loads((candidate / "metadata.json").read_text(encoding="utf-8"))
    if not metadata.get("contains_synthetic") and (metadata.get("dataset_provenance") or {}).get("publication_permitted") is not True: raise PermissionError("Research-only model cannot be approved for publication")
    if metadata.get("contains_synthetic"): raise ValueError("合成データで学習したモデルは承認できません")
    if metadata.get("rights_verified") is not True: raise ValueError("権利確認済みデータセットの来歴がないモデルは承認できません")
    if metadata.get("dataset_races", 0) < 100 or metadata.get("metrics", {}).get("races", 0) < 30: raise ValueError("実データまたは未使用期間の評価件数が不足しているため承認できません")
    if metadata.get("calibration_status") != "holdout_measured_reference_score": raise ValueError("確率校正のホールドアウト評価が記録されていません")
    approved_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    metadata["approval"] = "approved"; metadata["approved_at"] = approved_at
    (candidate / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    target = Path(registry_path); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps({"active_model": str(candidate), "approved_at": approved_at, "approved_manually": True}, ensure_ascii=False, indent=2), encoding="utf-8"); return target
