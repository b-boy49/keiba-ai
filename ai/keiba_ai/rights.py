"""Fail-closed provider rights and dataset provenance checks."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

VALID_RECORD_TYPES = {"races", "entries", "past_performances", "horses", "jockeys", "results", "training_features"}
VALID_PURPOSES = {"ingest", "internal_storage", "ml_training", "public_display", "redistribution"}

def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()

def _load_manifest(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("提供元権利台帳を読み込めません") from error
    if value.get("schema_version") != 1 or not isinstance(value.get("providers"), list):
        raise ValueError("提供元権利台帳の形式が不正です")
    return value

def get_provider(manifest_path: str | Path, provider_id: str) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    matches = [provider for provider in manifest["providers"] if provider.get("id") == provider_id]
    if len(matches) != 1: raise ValueError("提供元IDが未登録または重複しています")
    return matches[0]

def verify_provider_rights(manifest_path: str | Path, provider_id: str, record_type: str, purposes: set[str]) -> dict[str, Any]:
    if record_type not in VALID_RECORD_TYPES: raise ValueError("未定義のデータ種別です")
    if not purposes <= VALID_PURPOSES: raise ValueError("未定義の利用目的です")
    provider = get_provider(manifest_path, provider_id)
    if provider.get("approval_status") != "APPROVED": raise PermissionError("提供元は承認済みではありません")
    evidence = provider.get("evidence", [])
    if not evidence or any(not item.get("url") or not item.get("checked_at") or not item.get("reference") for item in evidence):
        raise PermissionError("利用許可の確認証跡が不足しています")
    scope = provider.get("record_type_permissions", {}).get(record_type)
    if not scope: raise PermissionError("このデータ種別は提供元の許可範囲外です")
    denied = [purpose for purpose in purposes if scope.get(purpose) is not True]
    if denied: raise PermissionError(f"用途別の許可がありません: {', '.join(sorted(denied))}")
    return provider

def provenance_path(dataset_path: str | Path) -> Path: return Path(f"{dataset_path}.provenance.json")

def write_provenance(dataset_path: str | Path, *, input_path: str | Path, rights_manifest: str | Path, provider: dict[str, Any], record_type: str, purposes: set[str], row_count: int) -> Path:
    target = provenance_path(dataset_path)
    permissions = provider.get("record_type_permissions", {}).get(record_type, {})
    payload = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(), "provider_id": provider["id"], "provider_name": provider.get("name", provider["id"]), "record_type": record_type, "authorized_purposes": sorted(purposes), "publication_permitted": permissions.get("public_display") is True and permissions.get("redistribution") is True, "rights_manifest_sha256": sha256_file(rights_manifest), "input_sha256": sha256_file(input_path), "dataset_sha256": sha256_file(dataset_path), "row_count": row_count, "evidence_references": [item["reference"] for item in provider["evidence"]], "is_synthetic": False}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target

def verify_dataset_purpose(dataset_path: str | Path, purpose: str) -> dict[str, Any]:
    if purpose not in VALID_PURPOSES: raise ValueError("未定義の利用目的です")
    sidecar = provenance_path(dataset_path)
    try: provenance = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise PermissionError("データ来歴がないため実データとして使用できません") from error
    if provenance.get("is_synthetic") is True: raise PermissionError("合成データは実データ用途に使用できません")
    if purpose not in provenance.get("authorized_purposes", []): raise PermissionError(f"来歴に {purpose} の許可がありません")
    if provenance.get("dataset_sha256") != sha256_file(dataset_path): raise ValueError("取込後にCSVが変更されています。再取込してください")
    return provenance

def write_prediction_provenance(predictions_path: str | Path, *, model_version: str, training_provenance: dict[str, Any] | None) -> Path:
    target = provenance_path(predictions_path)
    payload = {"schema_version": 1, "kind": "prediction_output", "created_at": datetime.now(timezone.utc).isoformat(), "dataset_sha256": sha256_file(predictions_path), "model_version": model_version, "training_provenance": training_provenance}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target

def verify_prediction_provenance(predictions_path: str | Path, model_version: str, provider_id: str) -> None:
    try: provenance = json.loads(provenance_path(predictions_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise PermissionError("予測出力の来歴がないため公開できません") from error
    if provenance.get("kind") != "prediction_output" or provenance.get("dataset_sha256") != sha256_file(predictions_path): raise ValueError("予測出力が変更されています")
    if provenance.get("model_version") != model_version or (provenance.get("training_provenance") or {}).get("provider_id") != provider_id: raise PermissionError("予測出力のモデルまたは学習提供元が一致しません")
