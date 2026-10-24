from __future__ import annotations

from pathlib import Path
import shutil
import pandas as pd
from .schema import REQUIRED_COLUMNS
from .csv_schemas import validate_entity_frame
from .rights import verify_provider_rights, verify_dataset_purpose, write_provenance

def read_race_csv(path: str | Path, *, require_outcome: bool = True) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(frame.columns) if require_outcome else (REQUIRED_COLUMNS - {"finish_position"}).difference(frame.columns)
    if missing:
        raise ValueError(f"CSVに必要な列がありません: {', '.join(sorted(missing))}")
    frame["race_date"] = pd.to_datetime(frame["race_date"], utc=True, errors="raise")
    if frame["race_id"].isna().any() or frame["horse_id"].isna().any():
        raise ValueError("race_id と horse_id は必須です")
    if require_outcome and (frame["finish_position"] <= 0).any():
        raise ValueError("finish_position は正の整数である必要があります")
    if frame.duplicated(["race_id", "horse_id"]).any():
        raise ValueError("race_id と horse_id の組み合わせが重複しています")
    numeric = ["distance_m", "recent_finish_avg", "distance_experience", "jockey_win_rate", "days_since_last_run", "dirt_2100_finish_avg", "tokyo_starts", "tokyo_finish_avg", "jockey_horse_starts", "jockey_horse_finish_avg"]
    for column in numeric: frame[column] = pd.to_numeric(frame[column], errors="raise")
    if (frame["distance_m"] <= 0).any() or (frame["days_since_last_run"] < 0).any() or ((frame["jockey_win_rate"] < 0) | (frame["jockey_win_rate"] > 1)).any():
        raise ValueError("特徴量に異常値があります")
    if not frame.get("is_synthetic", pd.Series(False, index=frame.index)).astype(bool).all():
        if "feature_as_of" not in frame.columns: raise ValueError("実データには特徴量の時点 feature_as_of が必要です")
        feature_as_of = pd.to_datetime(frame["feature_as_of"], utc=True, errors="raise")
        if (feature_as_of > frame["race_date"]).any(): raise ValueError("レース後の情報が特徴量に混入しています")
    return frame.sort_values(["race_date", "race_id", "horse_id"]).reset_index(drop=True)

def import_licensed_csv(input_path: str | Path, output_path: str | Path, source_name: str, rights_confirmed: bool, *, rights_manifest: str | Path | None = None, provider_id: str | None = None) -> Path:
    if not rights_confirmed or not rights_manifest or not provider_id:
        raise PermissionError("自己申告だけでは不十分です。--rights-confirmed、権利台帳、提供元IDが必要です。")
    provider = verify_provider_rights(rights_manifest, provider_id, "training_features", {"ingest", "internal_storage", "ml_training"})
    frame = read_race_csv(input_path)
    if "feature_as_of" not in frame.columns: raise ValueError("実データ取込には feature_as_of 列が必要です")
    frame["data_source"] = source_name or provider.get("name", provider_id)
    frame["is_synthetic"] = False
    target = Path(output_path); target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    write_provenance(target, input_path=input_path, rights_manifest=rights_manifest, provider=provider, record_type="training_features", purposes={"ingest", "internal_storage", "ml_training"}, row_count=len(frame))
    return target

def import_entity_csv(input_path: str | Path, output_path: str | Path, *, record_type: str, rights_manifest: str | Path, provider_id: str) -> Path:
    provider = verify_provider_rights(rights_manifest, provider_id, record_type, {"ingest", "internal_storage"})
    frame = validate_entity_frame(pd.read_csv(input_path), record_type)
    target = Path(output_path); target.parent.mkdir(parents=True, exist_ok=True); frame.to_csv(target, index=False)
    write_provenance(target, input_path=input_path, rights_manifest=rights_manifest, provider=provider, record_type=record_type, purposes={"ingest", "internal_storage"}, row_count=len(frame))
    return target

def load_authorized_training_csv(path: str | Path) -> pd.DataFrame:
    frame = read_race_csv(path)
    if frame.get("is_synthetic", pd.Series(False, index=frame.index)).astype(bool).all(): return frame
    frame.attrs["provenance"] = verify_dataset_purpose(path, "ml_training")
    return frame
