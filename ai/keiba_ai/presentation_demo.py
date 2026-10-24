"""Generate a local-only, rights-gated historical race demonstration.

This module has deliberately no web-server or Next.js dependency.  It uses the
chronological held-out cohort already used for one final evaluation only.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

import pandas as pd

from .all_dirt_research import _splits
from .data import load_authorized_training_csv
from .training import load_bundle, predict

DEMO_RACE_COUNT = 4
DISPLAY_FIELDS = ("recent_finish_avg", "dirt_2100_finish_avg", "tokyo_starts", "jockey_win_rate")


def _local_quarantine(path: str | Path) -> Path:
    value, root = Path(path).resolve(), Path("ai/quarantine").resolve()
    if value != root and root not in value.parents:
        raise PermissionError("Presentation demo artifacts must remain under ai/quarantine")
    return value


def select_demo_races(test: pd.DataFrame, count: int = DEMO_RACE_COUNT) -> list[str]:
    """Fixed earliest held-out races; selection does not inspect predictions/results."""
    dates = test[["race_id", "race_date"]].drop_duplicates().sort_values(["race_date", "race_id"])
    ids = dates["race_id"].astype(str).tolist()[:count]
    if len(ids) != count:
        raise ValueError(f"At least {count} held-out races are required")
    return ids


def _reason(row: pd.Series, race: pd.DataFrame) -> str:
    parts: list[str] = []
    recent = pd.to_numeric(race["recent_finish_avg"], errors="coerce")
    if pd.notna(row["recent_finish_avg"]) and row["recent_finish_avg"] <= recent.median():
        parts.append("recent pre-race finishing record was comparatively strong")
    if float(row.get("dirt_2100_finish_avg", 0) or 0) > 0 and row["dirt_2100_finish_avg"] <= pd.to_numeric(race["dirt_2100_finish_avg"], errors="coerce").replace(0, pd.NA).median():
        parts.append("prior dirt-2100m record was comparatively strong")
    if int(row.get("tokyo_starts", 0) or 0) > 0:
        parts.append("had prior Tokyo starts")
    if float(row.get("jockey_win_rate", 0) or 0) >= pd.to_numeric(race["jockey_win_rate"], errors="coerce").median():
        parts.append("jockey historical win rate was comparatively high")
    return "; ".join(parts[:2]) or "model used the complete pre-race feature profile; no single displayed factor dominated"


def _load_verified_names(path: str | Path, selected: pd.DataFrame) -> dict[tuple[str, str], str]:
    """Load a narrowly scoped, independently verified local-display allowlist."""
    mapping = pd.read_csv(path, dtype=str).fillna("")
    required = {"race_id", "horse_id", "horse_name", "source_url", "confirmed_at", "verification_status", "display_scope"}
    if missing := required - set(mapping.columns):
        raise ValueError(f"Horse-name mapping misses: {', '.join(sorted(missing))}")
    if not mapping["verification_status"].eq("CONFIRMED").all() or not mapping["display_scope"].eq("LOCAL_PRESENTATION").all():
        raise PermissionError("Only confirmed, local-presentation name records may be displayed")
    if not mapping["source_url"].str.startswith("https://www.jra.go.jp/").all():
        raise PermissionError("Horse-name mappings must cite an independently checked JRA official source")
    pd.to_datetime(mapping["confirmed_at"], utc=True, errors="raise")
    if mapping.duplicated(["race_id", "horse_id"]).any():
        raise ValueError("Horse-name mapping contains duplicate race/horse pairs")
    allowed = set(zip(selected["race_id"].astype(str), selected["horse_id"].astype(str)))
    rows = mapping.loc[mapping.apply(lambda row: (row["race_id"], row["horse_id"]) in allowed, axis=1)]
    return {(row.race_id, row.horse_id): row.horse_name for row in rows.itertuples(index=False)}


def _name(row: pd.Series, names: dict[tuple[str, str], str]) -> str:
    return names.get((str(row["race_id"]), str(row["horse_id"])), "Horse identity withheld (not independently confirmed)")


def create_presentation_demo(*, input_path: str | Path, model_dir: str | Path, output_dir: str | Path, rights_manifest: str | Path, provider_id: str, horse_name_mapping: str | Path | None = None, include_horse_names: bool = False) -> Path:
    """Create JSON + standalone HTML; never publishes or changes the selected model."""
    root, model = _local_quarantine(output_dir), _local_quarantine(model_dir)
    frame = load_authorized_training_csv(input_path)
    frame["race_date"] = pd.to_datetime(frame["race_date"], utc=True, errors="raise")
    metadata = load_bundle(model)["metadata"]
    if metadata.get("visibility") != "internal research only; never publish":
        raise PermissionError("Only an explicitly internal research model may be used for this demo")
    # Horse names are omitted by default.  They never come from the research
    # CSV: display uses only a separately verified official-source allowlist.
    names: dict[tuple[str, str], str] = {}
    if include_horse_names:
        if not horse_name_mapping:
            raise ValueError("--include-horse-names requires --horse-name-mapping")
    _, _, test, _ = _splits(frame)
    race_ids = select_demo_races(test)
    cohort = test.loc[test["race_id"].astype(str).isin(race_ids)].copy()
    prediction = predict(load_bundle(model), cohort)
    enriched = cohort.merge(prediction[["race_id", "horse_id", "predicted_rank", "reference_win_score"]], on=["race_id", "horse_id"], validate="one_to_one")
    if include_horse_names:
        names = _load_verified_names(horse_name_mapping, enriched)
    races = []
    for race_id in race_ids:
        race = enriched.loc[enriched["race_id"].astype(str).eq(race_id)].copy()
        top3 = race.sort_values("predicted_rank").head(3)
        actual = race.sort_values("finish_position").head(3)
        races.append({"race_id": race_id, "race_date": race["race_date"].iloc[0].date().isoformat(),
                      "field_size": int(len(race)), "predicted_top3": [
                          {"predicted_rank": int(row.predicted_rank), "horse_name": _name(pd.Series(row._asdict()), names),
                           "actual_finish": int(row.finish_position), "reason": _reason(pd.Series(row._asdict()), race)}
                          for row in top3.itertuples(index=False)],
                      "actual_top3": [{"finish_position": int(row.finish_position), "horse_name": _name(pd.Series(row._asdict()), names)} for row in actual.itertuples(index=False)]})
    root.mkdir(parents=True, exist_ok=True)
    # This is intentionally an ID-only backlog.  It never copies an unverified
    # horse name from the research dataset into a presentation artifact.
    all_pairs = enriched[["race_id", "horse_id"]].astype(str).drop_duplicates()
    all_pairs["verification_status"] = ["CONFIRMED" if (row.race_id, row.horse_id) in names else "UNCONFIRMED" for row in all_pairs.itertuples(index=False)]
    all_pairs.loc[all_pairs["verification_status"].eq("UNCONFIRMED")].to_csv(root / "unconfirmed-horse-names.csv", index=False)
    report = {"schema_version": 1, "visibility": "LOCAL_INTERNAL_ONLY", "name_display": "OFFICIAL_SOURCE_CONFIRMED" if include_horse_names else "WITHHELD", "selection": {"cohort": "chronological untouched Tokyo dirt 2100m test cohort", "rule": f"first {DEMO_RACE_COUNT} races by date and race ID; selection does not inspect results or predictions", "race_ids": race_ids}, "leakage_controls": {"feature_as_of": "each race date before same-day results are applied", "excluded_from_features": ["finish_position", "time", "finalt", "time_factor"], "model_tuning": "Validation only; this test cohort was not used for selection"}, "model": {"version": metadata["version"], "approval": metadata.get("approval"), "publication_permitted": False}, "display_limitations": "Names are sourced only from the independently verified JRA allowlist and are limited to local presentation. No research-dataset name is displayed or exported.", "races": races}
    (root / "presentation-demo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    sections = []
    for race in races:
        top = "".join(f"<li>AI #{x['predicted_rank']}: {escape(x['horse_name'])} — actual #{x['actual_finish']}<br><small>{escape(x['reason'])}</small></li>" for x in race["predicted_top3"])
        actual = ", ".join(f"#{x['finish_position']} {escape(x['horse_name'])}" for x in race["actual_top3"])
        sections.append(f"<section><h2>{escape(race['race_date'])} / {escape(race['race_id'])}</h2><p>Field: {race['field_size']}; actual top 3: {actual}</p><ol>{top}</ol></section>")
    page = "<!doctype html><meta charset='utf-8'><title>KEIBA AI — local research demo</title><style>body{font:16px system-ui;max-width:900px;margin:3rem auto;line-height:1.5}section{border-top:1px solid #ccc;padding:1rem 0}small{color:#444}</style><h1>KEIBA AI historical prediction demo</h1><p><strong>LOCAL INTERNAL ONLY.</strong> This is a fixed sample from the untouched chronological test cohort; it is not a claim of prospective performance.</p>" + "".join(sections) + "<hr><p>Source-display restriction: " + escape(report["display_limitations"]) + "</p>"
    # Replace the deliberately plain artifact with a self-contained presentation
    # surface.  It remains an offline file and reads no API or site data.
    styled_sections = []
    for race in races:
        top = "".join(f"<li><span class='rank r{x['predicted_rank']}'>{x['predicted_rank']}</span><div><b>{escape(x['horse_name'])}</b><small>Actual finish: <strong>{x['actual_finish']}</strong></small><p>{escape(x['reason'])}</p></div></li>" for x in race["predicted_top3"])
        actual = "".join(f"<li><span>{x['finish_position']}</span><b>{escape(x['horse_name'])}</b></li>" for x in race["actual_top3"])
        styled_sections.append(f"<section class='race-card'><header><div><p class='eyebrow'>TOKYO DIRT 2100M · HISTORICAL DEMO</p><h2>{escape(race['race_date'])}</h2><small>Race ID {escape(race['race_id'])} · Field {race['field_size']}</small></div><span class='local-chip'>LOCAL ONLY</span></header><div class='race-grid'><article><h3>AI Prediction Top 3</h3><ol class='predicted'>{top}</ol></article><aside><h3>Actual Top 3</h3><ol class='actual'>{actual}</ol></aside></div></section>")
    page = """<!doctype html><html lang='ja'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>KEIBA AI | Historical AI Demo</title><style>
:root{--ink:#eff1ea;--gold:#ebca6e;--line:rgba(228,202,116,.42)}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 90% 0,rgba(151,117,31,.2),transparent 31%),radial-gradient(ellipse at 3% 50%,rgba(36,102,60,.3),transparent 36%),#031d17;color:var(--ink);font-family:ui-serif,'Noto Serif JP',serif;line-height:1.5}.shell{width:min(1080px,calc(100% - 48px));margin:auto}.hero{padding:56px 0 42px;border-bottom:1px solid var(--line);background:linear-gradient(110deg,rgba(0,25,21,.96),rgba(0,31,25,.62))}.brand{font:700 39px/1 Georgia,serif;letter-spacing:1px}.brand i{font-style:normal;color:var(--gold)}.kicker{margin:24px 0 8px;color:#e5c368;font:11px Arial;letter-spacing:2px}.hero h1{margin:0;font-size:clamp(28px,5vw,48px);letter-spacing:2px}.hero p:last-child{max-width:700px;color:#cbd5cc;font-size:14px}.demo-grid{padding:30px 0 52px;display:grid;gap:17px}.race-card{overflow:hidden;border:1px solid var(--line);border-radius:12px;background:linear-gradient(130deg,rgba(4,47,37,.96),rgba(1,25,20,.94));box-shadow:0 12px 28px rgba(0,0,0,.24)}.race-card>header{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;padding:20px 24px;border-bottom:1px solid rgba(228,202,116,.22)}.eyebrow{margin:0;color:#d8b75d;font:10px Arial;letter-spacing:1.5px}.race-card h2{margin:2px 0;font-size:25px}.race-card header small{color:#aebcaf;font-size:11px}.local-chip{flex:none;border:1px solid var(--gold);border-radius:999px;color:#f1d986;padding:5px 9px;font:10px Arial;letter-spacing:1px}.race-grid{display:grid;grid-template-columns:1.65fr 1fr}.race-grid article,.race-grid aside{padding:20px 24px}.race-grid aside{border-left:1px solid rgba(228,202,116,.22);background:rgba(0,15,12,.2)}h3{margin:0 0 13px;font-size:15px;color:#f4db91}.predicted,.actual{list-style:none;padding:0;margin:0;display:grid;gap:8px}.predicted li{display:grid;grid-template-columns:33px 1fr;gap:12px;align-items:start;padding:10px;border-radius:7px;background:rgba(255,255,255,.045)}.rank{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:#47534d;color:#fff;font:bold 14px Arial}.r1{background:linear-gradient(135deg,#f5dd8c,#b88427);color:#1f281e}.r2{background:linear-gradient(135deg,#e8ece7,#88978f);color:#16211c}.r3{background:linear-gradient(135deg,#d89b62,#87582e);color:#fff}.predicted b,.actual b{display:block;font-size:16px}.predicted small{display:block;color:#b8c4ba;font-size:11px;margin-top:1px}.predicted small strong{color:#f0d477}.predicted p{margin:6px 0 0;color:#dbe2d9;font-size:12px;line-height:1.55}.actual li{display:flex;gap:10px;align-items:center;padding:11px 0;border-bottom:1px solid rgba(230,238,228,.12)}.actual li:last-child{border:0}.actual li span{color:#edcd74;font:bold 12px Arial;min-width:27px}.actual b{font-size:14px}.footer{border-top:1px solid var(--line);padding:24px 0 36px;color:#aeb9b0;font-size:11px}.footer strong{color:#ead388}@media(max-width:680px){.shell{width:min(100% - 28px,1080px)}.hero{padding:34px 0 28px}.brand{font-size:31px}.race-card>header,.race-grid article,.race-grid aside{padding:16px}.race-grid{grid-template-columns:1fr}.race-grid aside{border-left:0;border-top:1px solid rgba(228,202,116,.22)}.race-card h2{font-size:21px}.predicted b{font-size:15px}}</style><body><main><section class='hero'><div class='shell'><div class='brand'>KEIBA <i>AI</i></div><p class='kicker'>PRESENTATION MODE · LOCAL RESEARCH DEMO</p><h1>過去レース AI予想デモ</h1><p>2019年・東京ダート2100mの固定された未使用評価コホートから抽出。AI予想と実際の着順を比較します。</p></div></section><div class='shell demo-grid'>""" + "".join(styled_sections) + "</div></main><footer class='footer'><div class='shell'><strong>LOCAL INTERNAL ONLY.</strong> " + escape(report["display_limitations"]) + "</div></footer></body></html>"
    (root / "presentation-demo.html").write_text(page, encoding="utf-8")
    return root / "presentation-demo.html"
