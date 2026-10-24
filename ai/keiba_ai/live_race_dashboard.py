"""Standalone local dashboard for an approved configured-race prediction."""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

import pandas as pd

from .race_prediction import load_race_spec
from .rights import verify_dataset_purpose, verify_prediction_provenance


def create_live_race_dashboard(*, spec_path: str | Path, output_path: str | Path, entries_path: str | Path | None = None, prediction_path: str | Path | None = None, model_version: str | None = None, provider_id: str | None = None) -> Path:
    """Render an offline local HTML status page without a network request.

    Entries are shown only after their internal-storage provenance validates.
    Rankings additionally require prediction provenance, so a manually edited
    CSV cannot appear as model output.
    """
    output, quarantine = Path(output_path).resolve(), Path("ai/quarantine").resolve()
    if quarantine not in output.parents:
        raise PermissionError("Dashboard must remain under ai/quarantine")
    spec = load_race_spec(spec_path)
    entries = pd.DataFrame()
    if entries_path:
        verify_dataset_purpose(entries_path, "internal_storage")
        entries = pd.read_csv(entries_path, dtype=str).fillna("")
        entries = entries.loc[entries["race_id"].astype(str).eq(str(spec["race_id"]))].copy()
    prediction = pd.DataFrame()
    if prediction_path:
        if not model_version or not provider_id:
            raise ValueError("Prediction dashboard requires model_version and provider_id")
        verify_prediction_provenance(prediction_path, model_version, provider_id)
        prediction = pd.read_csv(prediction_path, dtype=str).fillna("")
        prediction = prediction.loc[prediction["race_id"].astype(str).eq(str(spec["race_id"]))].copy()
    merged = entries.merge(prediction[[c for c in ["horse_id", "predicted_rank", "reference_win_score", "generated_at", "model_version"] if c in prediction]], on="horse_id", how="left") if not entries.empty else entries
    if not merged.empty:
        merged["_rank"] = pd.to_numeric(merged.get("predicted_rank"), errors="coerce")
        merged = merged.sort_values(["_rank", "horse_no"], na_position="last")
    rows = "".join(
        f"<tr><td>{escape(str(getattr(row, 'horse_no', '')))}</td><td>{escape(str(getattr(row, 'gate_no', '')))}</td><td>{escape(str(getattr(row, 'horse_name', '')))}</td><td>{escape(str(getattr(row, 'jockey_name', '')))}</td><td>{escape(str(getattr(row, 'predicted_rank', '予測待ち')))}</td><td>{escape(str(getattr(row, 'reference_win_score', '')))}</td></tr>"
        for row in merged.itertuples(index=False)
    ) or '<tr><td colspan="6">承認済みの出馬表CSVを待機中です。馬名・順位は表示しません。</td></tr>'
    state = "予測完了" if not prediction.empty else ("出馬表確認済み・ID/成績待ち" if not entries.empty else "承認済み入力待ち")
    html = f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KEIBA AI | 新潟8R 研究用予測</title><style>:root{{--bg:#031d17;--card:#073427;--gold:#ebca6e;--ink:#f3f1e8}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,"Yu Gothic",sans-serif}}main{{max-width:1100px;margin:auto;padding:32px 18px}}header,section{{background:var(--card);border:1px solid #8a742e;border-radius:14px;padding:22px;margin-bottom:16px}}small{{color:var(--gold);letter-spacing:.08em}}h1{{margin:7px 0}}.state{{display:inline-block;border:1px solid var(--gold);padding:6px 10px;border-radius:99px;color:var(--gold)}}table{{border-collapse:collapse;width:100%;margin-top:16px}}th,td{{padding:11px 8px;text-align:left;border-bottom:1px solid #486158}}th{{color:var(--gold)}}p{{line-height:1.7}}@media(max-width:620px){{table{{font-size:12px}}th,td{{padding:8px 4px}}}}</style><main><header><small>LOCAL INTERNAL RESEARCH ONLY</small><h1>{escape(str(spec['race_name']))}</h1><p>{escape(str(spec['race_date']))}　{escape(str(spec['course_id']))} {escape(str(spec['race_no']))}R　ダート {escape(str(spec['distance_m']))}m</p><span class="state">{state}</span></header><section><h2>正式出馬表とAI予想</h2><table><thead><tr><th>馬番</th><th>枠番</th><th>馬名</th><th>騎手</th><th>AI順位</th><th>スコア</th></tr></thead><tbody>{rows}</tbody></table></section><section><h2>表示条件</h2><p>出馬表は権利確認済みCSVのみ、AI順位は予測provenanceを検証できたCSVのみ表示します。新潟ダート1800mは東京ダート2100m以外の未検証条件です。外部API・CDN・公開サイトには接続しません。</p></section></main></html>'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output
