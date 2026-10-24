"""Re-run full-field rankings for the fixed, untouched 2019 demo cohort."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

import pandas as pd

from .all_dirt_research import _splits
from .data import load_authorized_training_csv
from .presentation_demo import select_demo_races
from .rights import write_prediction_provenance
from .training import load_bundle, predict

WITHHELD = "非表示（JRA照合未完了）"
RACE_NAMES = {
    "201905040509": "昇仙峡特別",
    "201905040307": "3歳以上1勝クラス",
    "201905040610": "赤富士ステークス",
    "201905040706": "3歳以上1勝クラス",
}


def _quarantine(path: str | Path) -> Path:
    value, root = Path(path).resolve(), Path("ai/quarantine").resolve()
    if root not in value.parents:
        raise PermissionError("Historical ranking artifacts must remain under ai/quarantine")
    return value


def _verified_names(path: str | Path) -> dict[tuple[str, str], str]:
    source = pd.read_csv(path, dtype=str).fillna("")
    required = {"race_id", "horse_id", "horse_name", "source_url", "confirmed_at", "verification_status", "display_scope"}
    if missing := required - set(source.columns):
        raise ValueError(f"Name allowlist missing columns: {', '.join(sorted(missing))}")
    allowed = source.loc[
        source["verification_status"].eq("CONFIRMED")
        & source["display_scope"].eq("LOCAL_PRESENTATION")
        & source["source_url"].str.startswith("https://www.jra.go.jp/")
    ]
    if allowed.duplicated(["race_id", "horse_id"]).any():
        raise ValueError("Name allowlist contains duplicate race/horse rows")
    return {(str(row.race_id), str(row.horse_id)): str(row.horse_name) for row in allowed.itertuples(index=False)}


def _render(report: dict) -> str:
    payload = json.dumps(report, ensure_ascii=False).replace("<", "\\u003c")
    return f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KEIBA AI | 2019全頭再推論</title><style>:root{{--bg:#031d17;--panel:#073427;--gold:#ebca6e;--ink:#f3f1e8;--muted:#b6c5b8}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,"Yu Gothic",sans-serif}}main{{max-width:1120px;margin:auto;padding:30px 18px}}header,section{{background:var(--panel);border:1px solid rgba(235,202,110,.5);border-radius:14px;padding:22px;margin-bottom:16px}}small{{color:var(--gold);letter-spacing:.1em}}h1{{margin:8px 0;font-size:clamp(25px,4vw,38px)}}p{{line-height:1.65;color:var(--muted)}}.tabs{{display:flex;gap:8px;overflow:auto;margin-bottom:14px}}button{{color:var(--ink);background:#0b4b38;border:1px solid var(--gold);border-radius:8px;padding:9px 12px;white-space:nowrap;cursor:pointer}}button[aria-selected="true"]{{background:var(--gold);color:#15251f;font-weight:700}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:10px 7px;text-align:left;border-bottom:1px solid rgba(235,202,110,.2)}}th{{color:var(--gold)}}.medal{{font-weight:800;color:var(--gold)}}.actual{{color:#d4e0d5}}@media(max-width:580px){{main{{padding:16px 10px}}section,header{{padding:16px}}table{{font-size:12px}}th,td{{padding:8px 4px}}}}</style><main><header><small>LOCAL INTERNAL RESEARCH ONLY · RE-RUN FROM MODEL</small><h1>2019年 東京ダート2100m・全頭AI順位</h1><p>表示する順位・スコアはこのHTML生成時に既存LightGBMで再計算しました。実際の着順は特徴量・順位の計算に使わず、比較列にだけ表示します。馬名はJRA公式情報と照合済みのものだけを表示します。</p></header><section><div id="tabs" class="tabs"></div><div id="race"></div></section></main><script type="application/json" id="data">{payload}</script><script>(()=>{{const d=JSON.parse(document.getElementById('data').textContent);let i=0;const e=s=>String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));function draw(){{document.getElementById('tabs').innerHTML=d.races.map((r,n)=>`<button aria-selected="${{n===i}}" data-i="${{n}}">${{e(r.race_date)}}・東京${{r.race_no}}R</button>`).join('');const r=d.races[i];document.getElementById('race').innerHTML=`<h2>${{e(r.race_name)}} · ${{e(r.race_date)}} 東京${{r.race_no}}R · ダート2100m</h2><p>出走 ${{r.field_size}}頭 ／ 実名確認 ${{r.confirmed_name_count}}頭 ／ モデル ${{e(d.model_version)}}</p><table><thead><tr><th>AI順位</th><th>馬名</th><th>スコア</th><th>実際の着順（比較のみ）</th></tr></thead><tbody>${{r.runners.map(x=>`<tr><td class="${{x.predicted_rank<=3?'medal':''}}">${{x.predicted_rank}}</td><td>${{e(x.horse_name)}}</td><td>${{Number(x.reference_win_score).toFixed(6)}}</td><td class="actual">${{x.actual_finish}}着</td></tr>`).join('')}}</tbody></table>`;document.querySelectorAll('button[data-i]').forEach(b=>b.onclick=()=>{{i=Number(b.dataset.i);draw()}})}}draw()}})()</script></html>'''


def rerun_historical_full_rankings(*, input_path: str | Path, model_dir: str | Path, name_allowlist: str | Path, output_dir: str | Path) -> Path:
    """Recompute all rankings before joining a narrow verified-name allowlist."""
    root, model = _quarantine(output_dir), _quarantine(model_dir)
    bundle = load_bundle(model)
    metadata = bundle["metadata"]
    if metadata.get("visibility") != "internal research only; never publish":
        raise PermissionError("Only the internal research model may generate this artifact")
    frame = load_authorized_training_csv(input_path)
    frame["race_date"] = pd.to_datetime(frame["race_date"], utc=True, errors="raise")
    _, _, test, _ = _splits(frame)
    race_ids = select_demo_races(test)
    selected = test.loc[test["race_id"].astype(str).isin(race_ids)].copy()
    # Prediction uses the pre-race feature snapshot only. finish_position remains
    # outside the predict() feature builder and is joined only for comparison.
    scores = predict(bundle, selected)
    ranked = selected[["race_id", "race_date", "horse_id", "finish_position"]].merge(
        scores[["race_id", "horse_id", "reference_win_score"]], on=["race_id", "horse_id"], validate="one_to_one"
    )
    ranked = ranked.sort_values(["race_id", "reference_win_score", "horse_id"], ascending=[True, False, True], kind="stable")
    ranked["predicted_rank"] = ranked.groupby("race_id", sort=False).cumcount() + 1
    names = _verified_names(name_allowlist)
    ranked["horse_name"] = [names.get((str(row.race_id), str(row.horse_id)), WITHHELD) for row in ranked.itertuples(index=False)]
    ranked["name_verification"] = ["CONFIRMED" if value != WITHHELD else "UNCONFIRMED" for value in ranked["horse_name"]]
    ranked["model_version"] = metadata["version"]
    ranked["generated_at"] = datetime.now(timezone.utc).isoformat()
    ranked["visibility"] = "LOCAL_INTERNAL_ONLY"
    root.mkdir(parents=True, exist_ok=True)
    csv_path = root / "historical-2019-full-rankings.csv"
    ranked.to_csv(csv_path, index=False, encoding="utf-8")
    write_prediction_provenance(csv_path, model_version=metadata["version"], training_provenance=metadata.get("dataset_provenance"))
    races = []
    for race_id in race_ids:
        race = ranked.loc[ranked["race_id"].astype(str).eq(race_id)].copy()
        races.append({"race_id": race_id, "race_name": RACE_NAMES[race_id], "race_date": race["race_date"].iloc[0].date().isoformat(), "race_no": int(str(race_id)[-2:]), "field_size": len(race), "confirmed_name_count": int(race["name_verification"].eq("CONFIRMED").sum()), "runners": [{"predicted_rank": int(row.predicted_rank), "horse_name": row.horse_name, "reference_win_score": float(row.reference_win_score), "actual_finish": int(row.finish_position)} for row in race.itertuples(index=False)]})
    report = {"visibility": "LOCAL_INTERNAL_ONLY", "model_version": metadata["version"], "generated_at": datetime.now(timezone.utc).isoformat(), "selection": {"race_ids": race_ids, "source": "chronological untouched Tokyo dirt 2100m test cohort", "training_max": metadata["split"]["train_max"], "validation_max": metadata["split"]["validation"][1]}, "leakage_control": "finish_position is excluded from model features and shown only as an after-the-fact comparison", "races": races}
    (root / "historical-2019-full-rankings.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path = root / "historical-2019-full-rankings.html"
    html_path.write_text(_render(report), encoding="utf-8")
    return html_path
